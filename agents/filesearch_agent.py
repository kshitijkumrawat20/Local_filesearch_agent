"""
File search agent implementation using LangGraph.
"""
from typing import List
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
import psutil
from tools.file_tools import get_file_tools
from utils.state_manager import AgentState, StateManager
from config.settings import get_llm_config
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings   
from dotenv import load_dotenv
load_dotenv()

class FileSearchAgent:
    """AI agent for searching and managing files on Windows systems."""
    
    def __init__(self, api_key: str, root_dir: str = "C:\\"):
        self.api_key = api_key
        self.root_dir = root_dir
        # self.tools = get_file_tools(root_dir)
        self.file_tools_instance = None  # Store FileTools instance for cleanup
        self.tools = self._initialize_tools()
        self.llm = self._initialize_llm()
        self.memory = MemorySaver()
        self.graph = self._build_graph()
        self.state_manager = StateManager()

    def _initialize_tools(self):
        """Initialize tools and store the FileTools instance for cleanup."""
        from tools.file_tools import FileTools
        self.file_tools_instance = FileTools(root_dir=self.root_dir)
        return self.file_tools_instance.get_all_tools()
    
    def cleanup(self):
        """Clean up resources when agent session ends."""
        if self.file_tools_instance:
            try:
                print("[VERBOSE] Cleaning up FileSearchAgent session...")
                self.file_tools_instance.cleanup_session_vectorstores()
                print("[VERBOSE] ✅ Session cleanup completed")
            except Exception as e:
                print(f"[VERBOSE] Error during cleanup: {e}")
    
    def __del__(self):
        """Cleanup when agent is destroyed."""
        try:
            self.cleanup()
        except:
            pass

    
    def _initialize_llm(self) -> ChatGroq:
        """Initialize the language model."""
        config = get_llm_config()
        # return ChatGroq(
        #     model=config["model"],
        #     api_key=self.api_key,
        #     temperature=config["temperature"]
        # )

        return ChatOpenAI(
            model=config["model"],
            # temperature=0,
            # max_retries=2,
            api_key=self.api_key
        )
        # llm = ChatOllama(
        #     model="granite4:latest",
        #     temperature=0,
        #     # other params...
        # )
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        graph_builder = StateGraph(AgentState)
        
        # Bind tools to LLM
        llm_with_tools = self.llm.bind_tools(self.tools)
        
        def chatbot_node(state: AgentState):
            """Main chatbot node."""
            messages = state["messages"]
            
            try:
                response = llm_with_tools.invoke(messages)
                return {"messages": [response]}
                
            except Exception as e:
                error_msg = f"Error in chatbot_node: {str(e)}"
                return {
                    "messages": [AIMessage(content=error_msg)],
                    "error": error_msg
                }
        
        # Add nodes
        graph_builder.add_node("chatbot", chatbot_node)
        tool_node = ToolNode(tools=self.tools)
        graph_builder.add_node("tools", tool_node)
        
        # Add edges
        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.add_edge(START, "chatbot")
        
        return graph_builder.compile(checkpointer=self.memory)
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        result = ""
        for disk in psutil.disk_partitions(all = True):
            result += disk.device + ";"

        return """You are a helpful assistant designed to search files and folders on a Windows system with Network Attached Storage(NAS). You are optimized for finding files of types like PDF, DOCX, XLSX, and images, and querying their content.

### Your Capabilities:
- You have access to the following drives: **{result}**.
- The current directory provided for searching is: {self.root_dir}.
- If you require access to a specific drive that isn't listed or need to route a specific drive, always ask the user for the name of the drive.
- Use the **search file tool** to search for files and folders by name across all drives and directories.
- **File Operations:**
  - Use FileManagementToolkit's `list_directory` tool to list directories, files, and folders. The tool supports only allowed extensions, and directories are listed without extensions.
  - Do NOT use `list_directory` unless explicitly asked by the user to list files in a specific directory.

### **Document Querying Workflow** (IMPORTANT):
When a user wants to read or query a document's content, follow this TWO-STEP process:

**Step 1: Index the document first**
- Use `index_document` tool with the FULL file path
- Wait for confirmation that indexing is complete
- **REMEMBER THE FULL FILE PATH** - you'll need it for queries
- This only needs to be done ONCE per document per session

**Step 2: Query the indexed document**
- Use `query_document` tool with the **SAME FILE PATH** and the user's question
- You can use just the filename if only one document is indexed
- You can call this MULTIPLE TIMES with different questions
- **Always use the SAME file path from Step 1**
- No need to re-index unless it's a different document

**Step 3: Check what's indexed (optional)**
- Use `list_indexed_documents` to see what documents are available
- Helpful if you forget which documents are indexed

**Step 4: For small documents like resumes (optional but recommended)**
- Use `get_full_document_content` to get the COMPLETE document
- This is better than semantic search for small documents
- You'll see ALL sections: skills, projects, experience, etc.
- Only use this for documents < 5 pages (resumes, CVs, cover letters)

**Example workflow for RESUMES:**
```
User: "What's in my kshitijresume?"
Step 1: Search → Found: C:\\Users\\hp\\Downloads\\kshitijresume.pdf
Step 2: index_document("C:\\Users\\hp\\Downloads\\kshitijresume.pdf")
Step 3: get_full_document_content("kshitijresume.pdf")  ← Get EVERYTHING!
        ✅ Returns: Complete resume with all sections

Now answer ALL follow-up questions from the full content:
User: "What are the skills?"     → Answer from full content
User: "What are the projects?"   → Answer from full content  
User: "What are the tools?"      → Answer from full content
```

**Example workflow for LARGE documents:**
```
User: "What's in the 100-page report?"
Step 1: index_document("report.pdf")
Step 2: query_document("report.pdf", "What is the executive summary?")
Step 3: query_document("report.pdf", "What are the financial results?")
(Use semantic search for large docs, NOT get_full_document_content)
```

**Example workflow:**
```
User: "What's in my kshitijresume?"
Step 1: Search for file → Found: C:\\Users\\hp\\Downloads\\kshitijresume.pdf
Step 2: index_document("C:\\Users\\hp\\Downloads\\kshitijresume.pdf")
Step 3: query_document("C:\\Users\\hp\\Downloads\\kshitijresume.pdf", "What are the skills?")
        ✅ Returns: C++, Python, ML, NLP...

User: "What projects did he make?" (SAME document - remember the path!)
Step 4: query_document("C:\\Users\\hp\\Downloads\\kshitijresume.pdf", "What are the projects?")
        OR simply: query_document("kshitijresume.pdf", "What are the projects?")
        ✅ Uses SAME vectorstore, returns projects
```

**CRITICAL RULES:**
1. **NEVER** re-index for follow-up questions about the SAME document
2. **ALWAYS** use the same file path from the index step
3. You can use just the filename if there's only one indexed document
4. Use `list_indexed_documents` if you're unsure what's indexed
5. **For resumes/CVs**: Use `get_full_document_content` to get ALL sections at once
6. **For large docs**: Use `query_document` for semantic search

### Guidelines for File Search:
- **Search Strategy:** If the user requests to find a file with a specific name like "caste certificate," start by breaking the terms into partial queries, e.g., search for "caste" and then "certificate."
- **Combine Permutations:** Explore multiple combinations of the given query in sequence. For example:
  - For "pawan goel aadhar card," search first for "pawan," then "goel," then both combined ("pawan goel"), and finally "goel aadhar card."
  - For singular references like "kshitijResume," search for "kshitij" first, then combine it with "Resume," i.e., "kshitij Resume."
  - For simpler queries like "pancard," directly search for "pancard."
- Always try every relevant combination until a likely file is found.
- **File Does Not Exist Handling:** If no file is found after trying all systematic queries and permutations, clearly tell the user: "The file with the specified name does not exist."

### Query Optimization:
- Use **partial names** during a search because users might not remember the exact filenames. For instance:
  - If the user asks to search for 'caste certificate,' perform searches for both 'caste' and 'certificate.'
  - If a user asks for 'kshitijResume,' begin with 'kshitij' and then add 'Resume' for broader matching.
- Prioritize filenames that match completely and seem most relevant to user intent.
- Open files using their full Windows path format only after confirming their location.

### Guidance for Missing Files:
- **Help When Necessary**: Provide helpful suggestions if the file is not found. Encourage users to recheck names or provide additional details.
- Do not rely on assumptions about user folders, files, or paths unless explicitly listed.
- Always confirm file availability before reading its content or performing operations.

### General Instructions:
- Perform searches systematically for relevant directories and files.
- Open files or folder paths using full Windows formatting.
- Only open files if explicitly requested.
- **Remember**: For document content queries, ALWAYS use index_document first, then query_document. This allows multiple queries on the same document without re-indexing.

By carefully following the above approach, you will be able to assist users effectively in finding and managing their files!"""
    
    def process_message(self, user_input: str, thread_id: str = None, callbacks: List = None) -> dict:
        """Process a user message and return the response with streaming and optional callbacks."""
        import uuid
        
        # Auto-generate thread_id if not provided
        if thread_id is None:
            thread_id = str(uuid.uuid4())[:8]
            
        config = {"configurable": {"thread_id": thread_id}}
        
        # Add callbacks to config if provided
        if callbacks:
            config["callbacks"] = callbacks
        
        # Add system prompt to the first message if needed
        messages = [HumanMessage(content=f"{self.get_system_prompt()}\n\n{user_input}")]
        
        try:
            events = self.graph.stream(
                {"messages": messages},
                config,
                stream_mode="values",
            )
            
            responses = []
            verbose_info = {
                "tool_calls": [],
                "tool_responses": []
            }
            
            for event in events:
                if "messages" in event:
                    last_message = event["messages"][-1]
                    
                    # Extract tool calls for verbose display
                    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                        for tool_call in last_message.tool_calls:
                            verbose_info["tool_calls"].append({
                                "name": tool_call.get("name", "Unknown"),
                                "args": tool_call.get("args", {}),
                                "id": tool_call.get("id", "")
                            })
                    
                    # Extract tool responses
                    if hasattr(last_message, 'name') and hasattr(last_message, 'content'):
                        # This is a tool response message
                        verbose_info["tool_responses"].append({
                            "tool_name": last_message.name,
                            "content": last_message.content,
                            "tool_call_id": getattr(last_message, 'tool_call_id', '')
                        })
                    
                    # Create message with simplified verbose information
                    message_data = {
                        "type": "ai" if isinstance(last_message, AIMessage) else "human",
                        "content": last_message.content
                    }
                    
                    # Add tool calls and responses if available
                    if verbose_info["tool_calls"] or verbose_info["tool_responses"]:
                        message_data["tool_calls"] = verbose_info["tool_calls"]
                        message_data["tool_responses"] = verbose_info["tool_responses"]
                    
                    responses.append(message_data)
            
            return {
                "responses": responses,
                "verbose_info": verbose_info,
                "thread_id": thread_id,
                "success": True
            }
            
        except Exception as e:
            return {
                "responses": [{"type": "error", "content": f"Error: {str(e)}"}],
                "success": False
            }
