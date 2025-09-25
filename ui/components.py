"""
Streamlit UI components for the AI agents project.
"""
import streamlit as st
from typing import List, Dict, Any


class ChatUI:
    """Chat interface components for Streamlit."""
    
    @staticmethod
    def display_message(message: Dict[str, Any], avatar: str = None):
        """Display a chat message."""
        if message["type"] == "human":
            with st.chat_message("human", avatar="👤"):
                st.write(message["content"])
        elif message["type"] == "ai":
            with st.chat_message("assistant", avatar="🤖"):
                st.write(message["content"])
                
                # Show tool calls if available and enabled
                if st.session_state.get("show_tool_calls", True):
                    ChatUI._display_verbose_info(message)
                    
        elif message["type"] == "error":
            with st.chat_message("assistant", avatar="❌"):
                st.error(message["content"])
        elif message["type"] == "tool_call":
            with st.chat_message("assistant", avatar="🔧"):
                st.info(f"**Tool Call:** {message['tool_name']}")
                with st.expander("Tool Details", expanded=False):
                    st.write(f"**Arguments:** {message.get('arguments', {})}")
                    if message.get('result'):
                        st.write(f"**Result:** {message['result']}")
        elif message["type"] == "reasoning":
            with st.chat_message("assistant", avatar="🧠"):
                with st.expander("Agent Reasoning", expanded=False):
                    st.write(message["content"])
    
    @staticmethod
    def display_chat_history(messages: List[Dict[str, Any]]):
        """Display the entire chat history."""
        for message in messages:
            ChatUI.display_message(message)
    
    @staticmethod
    def _display_verbose_info(message: Dict[str, Any]):
        """Display simplified verbose information for AI messages."""
        if message.get("tool_calls"):
            with st.expander("🔧 Tool Calls", expanded=False):
                for tool_call in message["tool_calls"]:
                    st.write(f"**Tool:** {tool_call.get('name', 'Unknown')}")
                    if tool_call.get('args'):
                        st.code(str(tool_call.get('args', {})), language="json")
                    st.divider()
    
    @staticmethod
    def display_verbose_panel():
        """Display simplified verbose information in a dedicated panel."""
        if st.session_state.get("show_verbose_panel", False):
            with st.sidebar.expander("🔍 Tool Activity", expanded=True):
                if st.session_state.get("current_tool_calls"):
                    st.write("**Recent Tool Calls:**")
                    for tool_call in st.session_state.current_tool_calls[-5:]:  # Show last 5
                        st.text(f"• {tool_call}")
                
                if st.session_state.get("agent_status"):
                    st.write(f"**Status:** {st.session_state.agent_status}")
    
    @staticmethod
    def get_user_input(placeholder: str = "Type your message here...") -> str:
        """Get user input from chat input widget."""
        return st.chat_input(placeholder)


class SidebarUI:
    """Sidebar components for Streamlit."""
    
    @staticmethod
    def display_config_panel():
        """Display configuration panel in sidebar."""
        st.sidebar.header("⚙️ Configuration")
        
        # Root directory selection
        root_dir = st.sidebar.text_input(
            "Root Directory",
            value=st.session_state.get("root_dir", "C:\\"),
            help="Base directory for file searches"
        )
        
        # Display current thread ID (read-only)
        current_thread = st.session_state.get("thread_id", "Not set")
        st.sidebar.text_input(
            "Thread ID (Auto-generated)",
            value=current_thread,
            disabled=True,
            help="Unique identifier for this conversation (auto-generated)"
        )
        
        # Verbose settings
        st.sidebar.subheader("🔍 Debug Options")
        show_tool_calls = st.sidebar.checkbox(
            "Show Tool Calls",
            value=st.session_state.get("show_tool_calls", True),
            help="Display tool execution details"
        )
        
        show_verbose_panel = st.sidebar.checkbox(
            "Tool Activity Panel",
            value=st.session_state.get("show_verbose_panel", False),
            help="Show real-time tool activity panel"
        )
        
        # Update session state
        st.session_state.show_tool_calls = show_tool_calls
        st.session_state.show_verbose_panel = show_verbose_panel
        
        # Clear conversation button
        if st.sidebar.button("🗑️ Clear Conversation"):
            st.session_state.chat_history = []
            st.session_state.current_tool_calls = []
            st.session_state.agent_status = "Idle"
            # Generate new thread ID when clearing
            import uuid
            st.session_state.thread_id = str(uuid.uuid4())[:8]
            st.rerun()
        
        return root_dir
    
    @staticmethod
    def display_status_panel():
        """Display status information in sidebar."""
        st.sidebar.header("📊 Status")
        
        # Connection status
        if st.session_state.get("agent_initialized", False):
            st.sidebar.success("✅ Agent Ready")
        else:
            st.sidebar.error("❌ Agent Not Initialized")
        
        # Current directory
        current_dir = st.session_state.get("current_directory", "Unknown")
        st.sidebar.info(f"📁 Current: {current_dir}")
        
        # Message count
        message_count = len(st.session_state.get("chat_history", []))
        st.sidebar.metric("💬 Messages", message_count)
    
    @staticmethod
    def display_help_panel():
        """Display help information in sidebar."""
        with st.sidebar.expander("❓ How to Use"):
            st.write("""
            **File Search Agent Help:**
            
            1. **Search for files**: Ask to find specific files or folders
            2. **Open files**: Request to open files you've found
            3. **Navigate directories**: Explore folder structures
            4. **Ask questions**: Get help and guidance through conversation
            
            **Example queries:**
            - "Find my profile picture"
            - "Look for Excel files in Documents"
            - "Open the latest report"
            - "Show me folders in Desktop"
            - "Help me find files containing 'report'"
            - "What's in my Downloads folder?"
            """)


class MainUI:
    """Main UI components for the application."""
    
    @staticmethod
    def setup_page_config():
        """Configure the Streamlit page."""
        st.set_page_config(
            page_title="AI File Search Agent",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    @staticmethod
    def display_header():
        """Display the main header."""
        st.title("🔍 AI File Search Agent")
        st.markdown(
            "An intelligent assistant to help you find and manage files on your Windows system."
        )
    
    @staticmethod
    def display_connection_status():
        """Display connection and initialization status."""
        if not st.session_state.get("agent_initialized", False):
            st.error("⚠️ Agent not initialized. Please check your API key configuration.")
            return False
        return True
    
    @staticmethod
    def display_welcome_message():
        """Display welcome message for new users."""
        if not st.session_state.get("chat_history"):
            st.info("""
            👋 **Welcome to the AI File Search Agent!**
            
            I can help you:
            - Find files and folders on your system
            - Open documents and applications
            - Navigate directory structures
            - Provide file management assistance
            
            Just type your request below to get started!
            """)
    
    @staticmethod
    def display_error_message(error: str):
        """Display error message."""
        st.error(f"❌ Error: {error}")
    
    @staticmethod
    def display_success_message(message: str):
        """Display success message."""
        st.success(f"✅ {message}")