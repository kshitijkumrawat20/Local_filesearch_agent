"""
Main Streamlit application for the AI File Search Agent.
"""
import streamlit as st
import os
import sys
from typing import Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from agents.file_search_agent import FileSearchAgent
from config.settings import get_api_key, get_app_config, get_streamlit_config
from ui.components import ChatUI, SidebarUI, MainUI


class StreamlitApp:
    """Main Streamlit application class."""
    
    def __init__(self):
        self.config = get_streamlit_config()
        self.app_config = get_app_config()
        self.setup_session_state()
    
    def setup_session_state(self):
        """Initialize Streamlit session state."""
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        if "agent_initialized" not in st.session_state:
            st.session_state.agent_initialized = False
        
        if "agent" not in st.session_state:
            st.session_state.agent = None
        
        if "root_dir" not in st.session_state:
            st.session_state.root_dir = self.app_config["default_root_dir"]
        
        if "thread_id" not in st.session_state:
            import uuid
            st.session_state.thread_id = str(uuid.uuid4())[:8]
        
        if "current_directory" not in st.session_state:
            st.session_state.current_directory = self.app_config["default_root_dir"]
        
        # Initialize simplified verbose mode session state
        if "show_tool_calls" not in st.session_state:
            st.session_state.show_tool_calls = True
        
        if "show_verbose_panel" not in st.session_state:
            st.session_state.show_verbose_panel = False
        
        if "current_tool_calls" not in st.session_state:
            st.session_state.current_tool_calls = []
        
        if "current_tool_responses" not in st.session_state:
            st.session_state.current_tool_responses = []
        
        if "agent_status" not in st.session_state:
            st.session_state.agent_status = "Idle"
    
    def initialize_agent(self, api_key: str, root_dir: str) -> bool:
        """Initialize the file search agent."""
        try:
            if not api_key:
                st.error("❌ GROQ API key is required!")
                return False
            
            st.session_state.agent = FileSearchAgent(api_key, root_dir)
            st.session_state.agent_initialized = True
            st.session_state.root_dir = root_dir
            st.session_state.current_directory = root_dir
            return True
            
        except Exception as e:
            st.error(f"❌ Failed to initialize agent: {str(e)}")
            st.session_state.agent_initialized = False
            return False
    
    def process_user_message(self, user_input: str):
        """Process user message and update chat history with enhanced verbose display."""
        if not st.session_state.agent_initialized:
            MainUI.display_error_message("Agent not initialized")
            return
        
        # Add user message to history
        st.session_state.chat_history.append({
            "type": "human",
            "content": user_input
        })
        
        # Process with agent
        try:
            # Create a status container for agent activity
            status_placeholder = st.empty()
            activity_container = st.container()
            
            with status_placeholder:
                st.info("🤖 Agent is thinking...")
            
            response = st.session_state.agent.process_message(
                user_input, 
                st.session_state.thread_id
            )
            
            # Clear the thinking status
            status_placeholder.empty()
            
            # Display agent activity in the activity container
            if response["success"] and response.get("verbose_info"):
                verbose_info = response["verbose_info"]
                
                with activity_container:
                    if verbose_info.get("tool_calls") or verbose_info.get("tool_responses"):
                        st.success("✅ Agent completed processing")
                        with st.expander("🔧 Tool Usage Details", expanded=False):
                            # Display tool calls
                            if verbose_info.get("tool_calls"):
                                st.write("**🛠️ Tools Used:**")
                                for i, tc in enumerate(verbose_info["tool_calls"], 1):
                                    st.write(f"**{i}. Tool Used:** `{tc['name']}`")
                                    if tc.get('args'):
                                        st.json(tc['args'])
                                    st.write("---")
                            
                            # Display tool responses
                            if verbose_info.get("tool_responses"):
                                st.write("**📋 Tool Results:**")
                                for i, tr in enumerate(verbose_info["tool_responses"], 1):
                                    st.write(f"**Result {i} ({tr.get('tool_name', 'Unknown')}):**")
                                    response_content = tr.get('content', 'No response')
                                    if len(response_content) > 300:
                                        with st.expander(f"View Full Result {i}", expanded=False):
                                            st.text(response_content)
                                    else:
                                        st.info(response_content)
                                    st.write("---")
                
                # Update verbose session state
                st.session_state.current_tool_calls = [
                    f"{tc['name']}({tc.get('args', {})})" 
                    for tc in verbose_info.get("tool_calls", [])
                ]
                
                # Add tool responses to session state
                if "current_tool_responses" not in st.session_state:
                    st.session_state.current_tool_responses = []
                
                st.session_state.current_tool_responses = [
                    f"{tr.get('tool_name', 'Unknown')}: {tr.get('content', 'No response')[:100]}..." 
                    for tr in verbose_info.get("tool_responses", [])
                ]
                
                st.session_state.agent_status = "Processing completed"
                
                # Update thread_id if it was auto-generated
                if response.get("thread_id"):
                    st.session_state.thread_id = response["thread_id"]
                
                # Add AI responses to history
                for resp in response["responses"]:
                    if resp["type"] != "human":  # Don't duplicate user messages
                        st.session_state.chat_history.append(resp)
            else:
                st.session_state.chat_history.extend(response["responses"])
                st.session_state.agent_status = "Error occurred"
                
        except Exception as e:
            st.session_state.chat_history.append({
                "type": "error",
                "content": f"Error processing message: {str(e)}"
            })
            st.error(f"Error processing message: {str(e)}")
    
    def run(self):
        """Main application run method."""
        # Setup page configuration
        MainUI.setup_page_config()
        
        # Display header
        MainUI.display_header()
        
        # Initialize agent if not already done
        if not st.session_state.agent_initialized:
            try:
                api_key = get_api_key()
                self.initialize_agent(api_key, st.session_state.root_dir)
            except ValueError as e:
                st.error(str(e))
                st.stop()
        
        # Sidebar
        with st.sidebar:
            root_dir = SidebarUI.display_config_panel()
            
            # Update session state if root directory changed
            if root_dir != st.session_state.root_dir:
                st.session_state.root_dir = root_dir
                # Reinitialize agent with new root directory
                if st.session_state.agent_initialized:
                    try:
                        api_key = get_api_key()
                        self.initialize_agent(api_key, root_dir)
                    except ValueError as e:
                        st.error(str(e))
            
            SidebarUI.display_status_panel()
            SidebarUI.display_help_panel()
            
            # Display verbose panel if enabled
            ChatUI.display_verbose_panel()
        
        # Main content area
        if not MainUI.display_connection_status():
            st.stop()
        
        # Display welcome message for new users
        MainUI.display_welcome_message()
        
        # Chat history container
        chat_container = st.container()
        
        with chat_container:
            # Display chat history
            ChatUI.display_chat_history(st.session_state.chat_history)
        
        # Chat input
        user_input = ChatUI.get_user_input("Ask me to find files or folders...")
        
        if user_input:
            self.process_user_message(user_input)
            st.rerun()


def main():
    """Main entry point for the Streamlit app."""
    app = StreamlitApp()
    app.run()


# Add to app.py
import sys
import subprocess

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller executable
        import streamlit.web.cli as stcli
        sys.argv = ["streamlit", "run", __file__, "--server.headless", "true"]
        stcli.main()
    else:
        # Running normally
        main()