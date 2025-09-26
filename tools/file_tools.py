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
import requests
class FileTools:
    """Wrapper class for file management tools."""
    
    def __init__(self, root_dir: str = "C:\\"):
        self.root_dir = root_dir
        self.shell_tool = ShellTool()
        self.toolkit = FileManagementToolkit(root_dir=self.root_dir)
        self.file_management_tools = self.toolkit.get_tools()
    
    def get_all_tools(self) -> List:
        """Get all available tools."""
        return [
            # self.shell_tool,
            self.file_management_tools[6],  # List directory tool
            # list_all_subfolder_files,  # List directory tool
            # list_directory,
            open_file_tool,
            create_vector_store_and_query,
            search_file
        ]


@tool
def open_file_tool(file_path: str) -> str:
    """Open a file using the default system application by giving full path.Full path is must to open.
    
    Args:
        file_path: Full path to the file in Windows format to search for
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
        error_msg = f"Error creating vector store : {str(e)}"
        print(f"[VERBOSE] {error_msg}")
        return error_msg
    
@tool
def list_directory(directory_path: str, required_extension_file: List[str]) -> List[str]:
    """
    Lists all files in the specified directory and subdirectories.

    Args:
        directory_path (str): The path to the directory to scan.
        required_extension_file: Required file extension (e.g., .txt, .pdf,)

    Returns:
        list: A list of full file paths (strings) matching the criteria with allowed extension and without extension are folders.
    """
    print(f"[VERBOSE] Listing files in directory: {directory_path} with extensions: {required_extension_file}")
    toolkit = FileManagementToolkit()
    file_management_tools = toolkit.get_tools()
    list_dir = file_management_tools[6]  # Assuming the 7th tool is the list directory tool
    result = list_dir.invoke(input=directory_path)
    result= result.split("\n")
    print(f"[VERBOSE] Raw list directory result: {result}")
    # allowed_extensions = ('.pdf', '.ppt', '.pptx', '.xls', '.xlsx','.csv', '.doc', '.docx', '.jpg', '.jpeg', '.png')
    allowed_extensions = tuple(required_extension_file)
    
    filtered_files = []
    
    # Walk through only the specified directory with subdirectories
    for file in result:
        if (os.path.isfile(file) and file.lower().endswith(allowed_extensions)) or os.path.isdir(file):
            filtered_files.append(file)
            if os.path.isdir(file):
                # If it's a directory, list its contents (limited to 50 files)
                file_count = 0
                for root, dirs, files in os.walk(file):
                    for f in files:
                        if f.lower().endswith(allowed_extensions):
                            filtered_files.append(os.path.join(root, f))
                            file_count += 1
                            if file_count >= 50:
                                break
                    if file_count >= 50:
                        break

    # # Walk through directory and all subdirectories
    # for root, dirs, files in os.walk(directory_path):
    #     for i,file in enumerate(files):
    #         if file.lower().endswith(allowed_extensions):
    #             if i==0:
    #                 filtered_files.append(os.path.join(root, file))
    #             else:
    #                 filtered_files.append(os.path.join(file))
    print(f"[VERBOSE] Filtered files: {filtered_files}")
    return filtered_files

@tool 
def search_file(query:str)->str:
    """Search files using Everything Search Engine API. """
    url = f"http://127.0.0.1:8888/?s={query}&json=1&path_column=1"  # add json=1 to get JSON response
    resp = requests.get(url)
    # print(resp)
    resp.raise_for_status()
    file_paths = resp.json()
    print(file_paths)  # parse JSON response
    search_results = ''
    for file in file_paths['results']: 
        search_results += f"{file['path']+'\\'+file['name']} ;"
    print(search_results)
    return search_results


def get_file_tools(root_dir: str = "C:\\") -> List:
    """Factory function to get file tools."""
    file_tools = FileTools(root_dir)
    return file_tools.get_all_tools()