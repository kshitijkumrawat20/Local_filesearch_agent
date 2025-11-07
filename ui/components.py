"""
Streamlit UI components for the AI agents project with modern WhatsApp-like interface.
"""
import streamlit as st
from typing import List, Dict, Any
from datetime import datetime


class ChatUI:
    """Modern chat interface components for Streamlit."""
    
    @staticmethod
    def inject_custom_css():
        """Inject custom CSS for modern dark WhatsApp-like styling."""
        st.markdown("""
        <style>
        /* Hide default Streamlit elements */
        .stApp > header {
            background-color: transparent;
        }
        
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        }
        
        body {
            margin: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        }

        [data-testid="stAppViewContainer"] {
            padding-top: 0 !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            padding-top: 0 !important;
        }

        .block-container {
            padding-top: 2.5rem !important;
            margin-top: 0 !important;
        }

        /* Main container styling - Dark theme */
        .main > div {
            padding-top: 0 !important;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        
        /* Remove any top margin from first elements */
        .main .block-container {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        
        /* Compact Header styling - Dark */
        .chat-header {
            background: rgba(26, 26, 46, 0.95);
            backdrop-filter: blur(10px);
            padding: 0.8rem 1.5rem;
            border-radius: 0 0 15px 15px;
            box-shadow: 0 2px 20px rgba(0, 0, 0, 0.3);
            margin-bottom: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .chat-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: #ffffff;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .chat-subtitle {
            color: #b0b3c1;
            font-size: 0.85rem;
            margin-top: 0.1rem;
        }
        
        /* Chat messages area */
        .chat-messages {
            max-height: 65vh;
            overflow-y: auto;
            padding: 1rem;
            margin-bottom: 120px;
        }
        
        /* Message bubble styling - Dark theme */
        .message-bubble {
            max-width: 75%;
            margin-bottom: 1rem;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user-message {
            margin-left: auto;
        }
        
        .user-bubble {
            background: linear-gradient(135deg, #2c2c44 0%, #1f1f30 100%);
            color: #ffffff;
            padding: 12px 16px;
            border-radius: 18px 18px 4px 18px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
            position: relative;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }
        
        .ai-message {
            margin-right: auto;
        }
        
        .ai-bubble {
            background: rgba(45, 45, 65, 0.9);
            color: #ffffff;
            padding: 12px 16px;
            border-radius: 18px 18px 18px 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            position: relative;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .typing-bubble {
            background: rgba(45, 45, 65, 0.85);
            color: #ffffff;
            padding: 10px 14px;
            border-radius: 18px 18px 18px 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.08);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .typing-dot {
            width: 6px;
            height: 6px;
            background-color: rgba(255, 255, 255, 0.7);
            border-radius: 50%;
            animation: typingFade 1.4s infinite;
        }

        .typing-dot:nth-child(2) {
            animation-delay: 0.2s;
        }

        .typing-dot:nth-child(3) {
            animation-delay: 0.4s;
        }

        @keyframes typingFade {
            0%, 80%, 100% { opacity: 0.2; transform: translateY(0); }
            40% { opacity: 1; transform: translateY(-2px); }
        }
        
        .error-bubble {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 18px 18px 18px 4px;
            box-shadow: 0 2px 8px rgba(255, 107, 107, 0.3);
            position: relative;
        }
        
        /* Message timestamp */
        .message-time {
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.7);
            margin-top: 4px;
            text-align: right;
        }
        
        .ai-message .message-time {
            color: #95a5a6;
            text-align: left;
        }
        
        /* Avatar styling - Dark theme */
        .message-avatar {
            width: 35px;
            height: 35px;
            border-radius: 50%;
            margin-right: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.1rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        }
        
        /* Welcome message styling - Dark theme */
        .welcome-card {
            background: rgba(45, 45, 65, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 2rem;
            margin: 0.5rem 1rem 1rem 1rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }
        
        .welcome-card h2 {
            color: #ffffff;
            margin-bottom: 1rem;
        }
        
        /* Status indicators - Dark theme */
        .status-container {
            padding: 0.5rem 1rem;
            text-align: center;
            margin: 1rem 0;
        }
        
        .status-success {
            background: rgba(46, 204, 113, 0.2);
            color: #2ecc71;
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 0.9rem;
            display: inline-block;
            border: 1px solid rgba(46, 204, 113, 0.3);
        }
        
        .status-thinking {
            background: rgba(52, 152, 219, 0.2);
            color: #3498db;
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 0.9rem;
            display: inline-block;
            border: 1px solid rgba(52, 152, 219, 0.3);
        }
        
        /* Clear chat button - Dark theme */
        .stButton > button {
            background: rgba(231, 76, 60, 0.2) !important;
            color: #e74c3c !important;
            border-radius: 15px !important;
            border: 1px solid rgba(231, 76, 60, 0.3) !important;
            padding: 0.4rem 0.8rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            background: rgba(231, 76, 60, 0.3) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3) !important;
        }
        
        /* Input area styling - Dark theme */
        .stChatInput {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            background: rgba(26, 26, 46, 0.95) !important;
            backdrop-filter: blur(10px) !important;
            padding: 1rem !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        
        /* Streamlit elements dark theme */
        .stMarkdown {
            color: #ffffff;
        }
        
        .stInfo {
            background-color: rgba(52, 152, 219, 0.1) !important;
            border: 1px solid rgba(52, 152, 219, 0.3) !important;
            color: #ffffff !important;
        }
        
        .stSuccess {
            background-color: rgba(46, 204, 113, 0.1) !important;
            border: 1px solid rgba(46, 204, 113, 0.3) !important;
            color: #ffffff !important;
        }
        
        .stWarning {
            background-color: rgba(241, 196, 15, 0.1) !important;
            border: 1px solid rgba(241, 196, 15, 0.3) !important;
            color: #ffffff !important;
        }
        
        /* Hide scrollbar but keep functionality */
        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }
        
        .chat-messages::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }
        
        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.4);
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .message-bubble {
                max-width: 85%;
            }
            
            .chat-header {
                padding: 0.6rem 1rem;
            }
            
            .chat-title {
                font-size: 1.2rem;
            }
        }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def display_message(message: Dict[str, Any], avatar: str = None):
        """Display a chat message with WhatsApp-like styling."""
        timestamp = datetime.now().strftime("%H:%M")
        
        if message["type"] == "human":
            st.markdown(f"""
            <div class="message-bubble user-message">
                <div class="user-bubble">
                    {message["content"]}
                    <div class="message-time">{timestamp}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        elif message["type"] == "ai":
            st.markdown(f"""
            <div class="message-bubble ai-message">
                <div style="display: flex; align-items: flex-start;">
                    <div class="message-avatar">🤖</div>
                    <div class="ai-bubble" style="flex: 1;">
                        {message["content"]}
                        <div class="message-time">{timestamp}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        elif message["type"] == "error":
            st.markdown(f"""
            <div class="message-bubble ai-message">
                <div style="display: flex; align-items: flex-start;">
                    <div class="message-avatar">❌</div>
                    <div class="error-bubble" style="flex: 1;">
                        {message["content"]}
                        <div class="message-time">{timestamp}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif message["type"] == "typing":
            st.markdown("""
            <div class="message-bubble ai-message">
                <div style="display: flex; align-items: center;">
                    <div class="message-avatar">🤖</div>
                    <div class="typing-bubble">
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    @staticmethod
    def display_chat_history(messages: List[Dict[str, Any]]):
        """Display the entire chat history with modern styling."""
        if messages:
            st.markdown('<div class="chat-messages">', unsafe_allow_html=True)
            for message in messages:
                ChatUI.display_message(message)
            st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def display_status(status_type: str, message: str):
        """Display status messages with modern styling."""
        if status_type == "thinking":
            st.markdown(f"""
            <div class="status-container">
                <div class="status-thinking">
                    🤖 {message}
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif status_type == "success":
            st.markdown(f"""
            <div class="status-container">
                <div class="status-success">
                    ✅ {message}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    @staticmethod
    def get_user_input(placeholder: str = "Type your message here...") -> str:
        """Get user input from chat input widget."""
        return st.chat_input(placeholder)


class MainUI:
    """Main UI components for the application with modern styling."""
    
    @staticmethod
    def setup_page_config():
        """Configure the Streamlit page with modern settings."""
        st.set_page_config(
            page_title="AI File Search Agent",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
    
    @staticmethod
    def display_header():
        """Display the compact dark chat header."""
        st.markdown("""
        <div class="chat-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="chat-title">
                        🔍 AI File Search Agent
                    </div>
                    <div class="chat-subtitle">
                        Your intelligent file management assistant
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Clear chat button (positioned in a separate small container)
        col1, col2 = st.columns([8, 1])
        with col2:
            if st.button("🗑️", key="clear_chat", help="Clear conversation history"):
                st.session_state.chat_history = []
                import uuid
                st.session_state.thread_id = str(uuid.uuid4())[:8]
                st.rerun()
    
    @staticmethod
    def display_connection_status():
        """Display connection and initialization status."""
        if not st.session_state.get("agent_initialized", False):
            st.markdown("""
            <div class="welcome-card">
                <h3>⚠️ Agent Initializing...</h3>
                <p>Please wait while we set up your AI assistant.</p>
            </div>
            """, unsafe_allow_html=True)
            return False
        return True
    
    @staticmethod
    def display_welcome_message():
        """Display modern welcome message for new users."""
        if not st.session_state.get("chat_history"):
            # Simple welcome text without card styling
            st.markdown("""
            <div style=\"text-align: center; padding: 0 1rem 1rem; color: #ffffff; margin: 0;\">
                <h2 style=\"color: #ffffff; margin: 0 0 1rem;\">👋 Welcome to AI File Search!</h2>
                <p style=\"font-size: 1.1rem; color: #b0b3c1; margin: 0 0 1rem;\">
                    I'm your intelligent assistant ready to help you find and manage files on your system.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Create feature cards using Streamlit columns
            st.markdown("### 🚀 What I can do:")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("""
                **🔍 Smart Search**  
                Find files by name, type, or content
                """)
                st.success("""
                **🤖 AI Assistance**  
                Natural language file operations
                """)
            
            with col2:
                st.info("""
                **📂 File Management**  
                Open, and navigate folders
                """)
                st.warning("""
                **⚡ Quick Actions**  
                Instant file opening and navigation
                """)
            
            # Examples section
            st.markdown("### 💬 Try these examples:")
            st.markdown("""
            - *"Find my Excel files from last week"*
            - *"Open my Documents folder"*  
            - *"Look for files containing 'budget'"*
            - *"Show me my recent downloads"*
            """)
            
            st.markdown("""
            <p style="text-align: center; margin-top: 2rem; color: #95a5a6; font-style: italic;">
                Just type your request below to get started! 🎯
            </p>
            """, unsafe_allow_html=True)
        else:
            # Show clear chat button when there's chat history
            col1, col2, col3 = st.columns([4, 1, 4])
            with col2:
                if st.button("🗑️ Clear Chat", key="clear_chat_history"):
                    st.session_state.chat_history = []
                    import uuid
                    st.session_state.thread_id = str(uuid.uuid4())[:8]
                    st.rerun()
    
    @staticmethod
    def display_error_message(error: str):
        """Display error message with modern styling."""
        st.markdown(f"""
        <div class="message-bubble ai-message">
            <div style="display: flex; align-items: flex-start;">
                <div class="message-avatar">❌</div>
                <div class="error-bubble" style="flex: 1;">
                    <strong>Error:</strong> {error}
                    <div class="message-time">{datetime.now().strftime("%H:%M")}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def display_success_message(message: str):
        """Display success message with modern styling."""
        ChatUI.display_status("success", message)