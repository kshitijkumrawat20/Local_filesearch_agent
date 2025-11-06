"""
State management for the file search agent.
"""
from typing import TypedDict, List, Annotated
from langchain.schema import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State schema for the agent graph."""
    messages: Annotated[List[BaseMessage], add_messages]
    current_directory: str
    search_results: List[str]


class StateManager:
    """Manager for agent state operations."""
    
    @staticmethod
    def create_initial_state(root_dir: str = "C:\\") -> AgentState:
        """Create initial state for the agent."""
        return {
            "messages": [],
            "current_directory": root_dir,
            "search_results": []
        }
    
    @staticmethod
    def update_state(state: AgentState, **updates) -> AgentState:
        """Update state with new values."""
        new_state = state.copy()
        for key, value in updates.items():
            if key in new_state:
                new_state[key] = value
        return new_state