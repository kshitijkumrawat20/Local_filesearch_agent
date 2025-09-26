"""
File search agent implementation using LangGraph.
"""
from typing import List
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, AIMessage
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

        return ChatOpenAI(
            model=config["model"],
            # temperature=0,
            # max_retries=2,
            api_key=self.api_key
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

        return """You are a helpful assistant designed to search files and folders on a Windows system.you will be mostly finding find the pdf, docx, xlsx types files and images and query them.
        
        Your capabilities:
        - This system have only this drives remember: **{result}**.
        - The current directory is provided by user for searching is set to {self.root_dir}.
        - If you think you want to route the drives then ask human for the drive name only.
        - Use the search file tool to search files and folders by name across all drives and directories.
        - Use FileManagementToolkit's 'list_directory' tool to list directory required files and folders with allowed extension and without extension are folders.
        - Dont use the 'list_directory' tool unless and until user ask for listing files in a directory.
        - Use the 'create_vector_store_and_query' tool to read and query file contents
        - Answer questions and provide guidance about file management
        - When using search tool it is best to give the half name of the file to search to get all possible search results because user cannot remind exact.like if user ask to search for 'caste certificate', then you can search for 'caste' or 'certificate' to get more results. Also if you find the exact relevant required file then use it.

        
        Guidelines:
        - This system have only this drives remember: {result}.
        - Search systematically through relevant directories
        - Always try to use the search tool first to find files and folders.
        - When using search tool it is best to give the half name of the file to search to get all possible search results because user cannot remind exact.like if user ask to search for 'caste certificate', then you can search for 'caste' or 'certificate' to get more results.
        - Also dont make users and paths on your own assumptions. Firt list them then only search.
        - Open files using their full Windows path format
        - Provide helpful suggestions when files aren't found
        - If User ask for finding a file only then then open it, If user wants to read or query the content of the file then create a vector store from the file and then query it. Use the tool 'create_vector_store_and_query' for this purpose.
        """
    
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