"""
Configuration settings for the AI agents project.
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_api_key() -> str:
    """Get the OpenAI API key from environment variables."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return api_key


def get_llm_config() -> Dict[str, Any]:
    """Get LLM configuration settings with fallback options."""
    # Check which API keys are available
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    
    # Prefer OpenAI, fallback to Groq if available
    if has_openai:
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",  # More cost-effective, good for file search
            "temperature": 0.1,
            "max_tokens": 2048,
            "max_retries": 3,
            "timeout": 60
        }
    elif has_groq:
        return {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",  # Fast and capable
            "temperature": 0.1,
            "max_tokens": 2048,
            "max_retries": 3,
            "timeout": 60
        }
    else:
        # Last resort: use local Ollama if installed
        return {
            "provider": "ollama",
            "model": "llama3.2:latest",
            "temperature": 0.1,
            "max_tokens": 2048,
            "timeout": 120
        }


def get_app_config() -> Dict[str, Any]:
    """Get application configuration settings."""
    return {
        "default_root_dir": "C:\\",
        "app_title": "AI File Search Agent",
        "page_icon": "🔍",
        "layout": "wide"
    }


def get_streamlit_config() -> Dict[str, Any]:
    """Get Streamlit-specific configuration."""
    return {
        "page_title": "File Search Agent",
        "sidebar_width": 300,
        "chat_max_messages": 100,
        "enable_dark_theme": True
    }
