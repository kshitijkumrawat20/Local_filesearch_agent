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


class FileSearchAgent:
    """AI agent for searching and managing files on Windows systems."""
    
    def __init__(self, api_key: str, root_dir: str = "C:\\"):
        self.api_key = api_key
        self.root_dir = root_dir
        # self.tools = get_file_tools(root_dir)
        self.tools = get_file_tools()
        self.llm = self._initialize_llm()
        self.memory = MemorySaver()
        self.graph = self._build_graph()
        self.state_manager = StateManager()
    
    def _initialize_llm(self) -> ChatGroq:
        """Initialize the language model."""
        config = get_llm_config()
        # return ChatGroq(
        #     model=config["model"],
        #     api_key=self.api_key,
        #     temperature=config["temperature"]
        # )

        # return ChatOpenAI(
        #     model=config["model"],
        #     # temperature=0,
        #     # max_retries=2,
        #     api_key=self.api_key
        # )
        llm = ChatOllama(
            model="granite4:latest",
            temperature=0,
            # other params...
        )
    
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
        for disk in psutil.disk_partitions():
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
  - Use the `create_vector_store_and_query` tool to read and query file contents when a user wants to search inside a file.

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
- If the user wants to read or query the file’s content, create a vector store from the file and then query its content using the `create_vector_store_and_query` tool.

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
