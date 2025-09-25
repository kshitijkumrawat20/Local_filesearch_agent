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
    """Get LLM configuration settings."""
    return {
        "model": "gpt-4o-mini",  # or "qwen/qwen3-32b"
        "temperature": 0.1,
        "max_tokens": 2048
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