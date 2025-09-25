"""
File management and shell tools for the AI agent.
"""
import os
from langchain_community.tools import ShellTool
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools import tool
from typing import List


class FileTools:
    """Wrapper class for file management tools."""
    
    def __init__(self, root_dir: str = "C:\\"):
        self.root_dir = root_dir
        self.shell_tool = ShellTool()
        self.toolkit = FileManagementToolkit()
        self.file_management_tools = self.toolkit.get_tools()
    
    def get_all_tools(self) -> List:
        """Get all available tools."""
        return [
            self.shell_tool,
            self.file_management_tools[6],  # List directory tool
            open_file_tool
        ]


@tool
def open_file_tool(file_path: str) -> str:
    """Open a file using the default system application.
    
    Args:
        file_path: Full path to the file in Windows format
        
    Returns:
        Success message with verbose information
    """
    try:
        # Add verbose logging
        print(f"[VERBOSE] Attempting to open file: {file_path}")
        
        if not os.path.exists(file_path):
            error_msg = f"File does not exist: {file_path}"
            print(f"[VERBOSE] {error_msg}")
            return error_msg
        
        os.startfile(file_path)
        success_msg = f"Successfully opened file: {file_path}"
        print(f"[VERBOSE] {success_msg}")
        return success_msg
    except Exception as e:
        error_msg = f"Error opening file {file_path}: {str(e)}"
        print(f"[VERBOSE] {error_msg}")
        return error_msg


def get_file_tools(root_dir: str = "C:\\") -> List:
    """Factory function to get file tools."""
    file_tools = FileTools(root_dir)
    return file_tools.get_all_tools()