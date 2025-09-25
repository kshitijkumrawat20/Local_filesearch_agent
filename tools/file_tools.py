"""
File management and shell tools for the AI agent.
"""
import os
from langchain_community.tools import ShellTool
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools import tool
from typing import List
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyMuPDFLoader, Docx2txtLoader
from langchain_community.document_loaders import UnstructuredExcelLoader

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
            open_file_tool,
            create_vector_store_and_query
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

@tool
def create_vector_store_and_query(file_path: str, query: str) -> str:
    """Create a vector store from files path given and query it."""
    try:
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return f"File does not exist: {file_path}"

        documents = []
        if file_path.lower().endswith('.pdf'):
            loader = PyMuPDFLoader(file_path)
            documents.extend(loader.load())
        elif file_path.lower().endswith('.docx'):
            loader = Docx2txtLoader(file_path)
            documents.extend(loader.load())
        elif file_path.lower().endswith('.xlsx'):
            loader = UnstructuredExcelLoader(file_path)
            documents.extend(loader.load())
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                documents.append(Document(page_content=content))
        
        # Create an in-memory Chroma instance
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small",api_key=os.getenv("OPENAI_API_KEY"))
        vector_store = Chroma(
            collection_name="my_in_memory_collection",
            embedding_function=embeddings,
        )
        vector_store.add_documents(documents)

        results = vector_store.similarity_search(query, k=5)

        # Process the results as needed
        for result in results:
            print(f"Found similar document: {result}")
        result_summaries = [doc.page_content[:200] + "..." for doc in results]
        return "\n\n".join(result_summaries)
        # Save the vector store to a persistent location if needed
        # vector_store.persist("path_to_persist_vector_store")
        
    except Exception as e:
        error_msg = f"Error creating vector store from {directory}: {str(e)}"
        print(f"[VERBOSE] {error_msg}")
        return error_msg
    

def get_file_tools(root_dir: str = "C:\\") -> List:
    """Factory function to get file tools."""
    file_tools = FileTools(root_dir)
    return file_tools.get_all_tools()