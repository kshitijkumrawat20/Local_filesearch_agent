"""
File search agent implementation using LangGraph.
"""
from typing import List
import os
import logging
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

logger = logging.getLogger(__name__)

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
        """Initialize the language model with fallback support."""
        config = get_llm_config()
        provider = config.get("provider", "openai")
        
        try:
            if provider == "openai":
                logger.info(f"🤖 Initializing OpenAI: {config['model']}")
                return ChatOpenAI(
                    model=config["model"],
                    temperature=config["temperature"],
                    max_retries=config.get("max_retries", 3),
                    timeout=config.get("timeout", 60),
                    api_key=self.api_key
                )
            elif provider == "groq":
                logger.info(f"🤖 Initializing Groq: {config['model']}")
                return ChatGroq(
                    model=config["model"],
                    api_key=os.getenv("GROQ_API_KEY"),
                    temperature=config["temperature"],
                    max_retries=config.get("max_retries", 3),
                    timeout=config.get("timeout", 60)
                )
            elif provider == "ollama":
                logger.info(f"🤖 Initializing Ollama: {config['model']}")
                return ChatOllama(
                    model=config["model"],
                    temperature=config["temperature"],
                    timeout=config.get("timeout", 120)
                )
            else:
                # Default fallback to OpenAI
                logger.warning(f"Unknown provider '{provider}', defaulting to OpenAI")
                return ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0.1,
                    max_retries=3,
                    api_key=self.api_key
                )
                
        except Exception as e:
            logger.error(f"Failed to initialize {provider}: {e}")
            # Try fallback to Groq
            if provider != "groq" and os.getenv("GROQ_API_KEY"):
                logger.info("🔄 Falling back to Groq...")
                return ChatGroq(
                    model="llama-3.3-70b-versatile",
                    api_key=os.getenv("GROQ_API_KEY"),
                    temperature=0.1
                )
            else:
                raise Exception(f"Failed to initialize any LLM provider: {e}")
    
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
        """Get the system prompt for the agent from prompt.txt file."""
        result = ""
        for disk in psutil.disk_partitions(all = True):
            result += disk.device + ";"

        # Load prompt from prompt.txt file
        prompt_file = os.path.join(os.path.dirname(__file__), "prompt.txt")
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
            
            # Replace placeholders with actual values
            prompt = prompt_template.replace("{result}", result)
            prompt = prompt.replace("{self.root_dir}", self.root_dir)
            
            return prompt
        except FileNotFoundError:
            logger.error(f"prompt.txt not found at {prompt_file}")
            return """You are a helpful assistant designed to search files and folders on a Windows system with Network Attached Storage(NAS). You are optimized for finding files of types like PDF, DOCX, XLSX, and images, and querying their content.

### Fallback prompt if file not found ###"""
    
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
