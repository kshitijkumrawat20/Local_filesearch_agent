"""
Main Streamlit application for the AI File Search Agent.
"""
import streamlit as st
import os
import sys
import uuid
from typing import Dict, Any

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from agents.file_search_agent import FileSearchAgent
from config.settings import get_api_key, get_app_config, get_streamlit_config
from ui.components import ChatUI, MainUI


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
    
    def process_user_message(self, user_input: str, chat_placeholder=None):
        """Process user message and update chat history with modern UI."""
        if not st.session_state.agent_initialized:
            MainUI.display_error_message("Agent not initialized")
            return

        # Add user message to history
        st.session_state.chat_history.append({
            "type": "human",
            "content": user_input
        })

        if chat_placeholder is not None:
            with chat_placeholder.container():
                ChatUI.display_chat_history(st.session_state.chat_history)

        # Add typing indicator to history
        typing_id = str(uuid.uuid4())
        typing_message = {
            "type": "typing",
            "id": typing_id
        }
        st.session_state.chat_history.append(typing_message)

        if chat_placeholder is not None:
            with chat_placeholder.container():
                ChatUI.display_chat_history(st.session_state.chat_history)

        try:
            response = st.session_state.agent.process_message(
                user_input,
                st.session_state.thread_id
            )
        except Exception as exc:
            # Remove typing indicator
            if st.session_state.chat_history and st.session_state.chat_history[-1].get("type") == "typing":
                st.session_state.chat_history.pop()
            else:
                st.session_state.chat_history = [msg for msg in st.session_state.chat_history if msg.get("type") != "typing"]

            st.session_state.chat_history.append({
                "type": "error",
                "content": f"Error processing message: {str(exc)}"
            })

            if chat_placeholder is not None:
                with chat_placeholder.container():
                    ChatUI.display_chat_history(st.session_state.chat_history)
            return

        # Remove typing indicator after successful response
        if st.session_state.chat_history and st.session_state.chat_history[-1].get("type") == "typing":
            st.session_state.chat_history.pop()
        else:
            st.session_state.chat_history = [msg for msg in st.session_state.chat_history if msg.get("type") != "typing"]

        if response["success"]:
            # Update thread_id if it was auto-generated
            if response.get("thread_id"):
                st.session_state.thread_id = response["thread_id"]

            # Consolidate AI responses into a single message
            ai_responses = [resp for resp in response["responses"] if resp["type"] == "ai"]
            if ai_responses:
                combined_content = "\n\n".join([resp["content"] for resp in ai_responses])
                st.session_state.chat_history.append({
                    "type": "ai",
                    "content": combined_content
                })

            # Add any non-AI responses (like errors) separately
            for resp in response["responses"]:
                if resp["type"] not in ["human", "ai"]:
                    st.session_state.chat_history.append(resp)
        else:
            # For unsuccessful responses, still consolidate AI messages
            ai_responses = [resp for resp in response["responses"] if resp["type"] == "ai"]
            if ai_responses:
                combined_content = "\n\n".join([resp["content"] for resp in ai_responses])
                st.session_state.chat_history.append({
                    "type": "ai",
                    "content": combined_content
                })

            # Add any error or other messages
            for resp in response["responses"]:
                if resp["type"] not in ["human", "ai"]:
                    st.session_state.chat_history.append(resp)

        if chat_placeholder is not None:
            with chat_placeholder.container():
                ChatUI.display_chat_history(st.session_state.chat_history)
    
    def run(self):
        """Main application run method with modern UI."""
        # Setup page configuration
        MainUI.setup_page_config()
        
        # Inject custom CSS for modern styling
        ChatUI.inject_custom_css()
        
        # Initialize agent if not already done
        if not st.session_state.agent_initialized:
            try:
                api_key = get_api_key()
                self.initialize_agent(api_key, st.session_state.root_dir)
            except ValueError as e:
                st.error(str(e))
                st.stop()
        
        # Display welcome message for new users
        MainUI.display_welcome_message()
        
        # Chat history with modern styling
        chat_placeholder = st.empty()
        with chat_placeholder.container():
            ChatUI.display_chat_history(st.session_state.chat_history)
        
        # Chat input at bottom
        user_input = ChatUI.get_user_input("Type your message here...")
        
        if user_input:
            self.process_user_message(user_input, chat_placeholder)
            st.rerun()
    # Layout handled via global styles


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
        try:
            import streamlit.web.cli as stcli  # type: ignore
        except ModuleNotFoundError:  # pragma: no cover - fallback for different Streamlit versions
            from streamlit.web import cli as stcli  # type: ignore
        sys.argv = ["streamlit", "run", __file__, "--server.headless", "true"]
        stcli.main()
    else:
        # Running normally
        main()