import base64
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
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from utils.sementic_search_engine import Detect_and_Create_file_VStore

# Add pandas and openpyxl for Excel handling
try:
    import pandas as pd
    import openpyxl
    EXCEL_DEPS_AVAILABLE = True
except ImportError:
    EXCEL_DEPS_AVAILABLE = False
    print("[WARNING] pandas or openpyxl not installed. Excel file reading will be limited.")

class FileTools:
    """Wrapper class for file management tools."""
    
    def __init__(self, root_dir: str = "C:\\"):
        self.root_dir = root_dir
        self.shell_tool = ShellTool()
        self.toolkit = FileManagementToolkit(root_dir=self.root_dir)
        self.file_management_tools = self.toolkit.get_tools()
        self.vectorstore = self.get_vectorstore()

    def get_vectorstore(self):
        try:
            # Check if the database actually has content
            embeddings = OpenAIEmbeddings()
            vs = Chroma(collection_name="paths", embedding_function=embeddings, persist_directory="./chroma_db")
            
            # Verify the vectorstore has content by trying to get count
            try:
                # Try to get a sample of documents to verify database has content
                sample_docs = vs.similarity_search("test", k=1)
                collection_count = vs._collection.count()
                
                if collection_count == 0:
                    print("[VERBOSE] Chroma DB exists but is empty, rebuilding...")
                    raise Exception("Empty vectorstore detected")
                
                print(f"[VERBOSE] Loaded existing vectorstore with {collection_count} documents")
                return vs
                
            except Exception as count_error:
                print(f"[VERBOSE] Vectorstore verification failed: {str(count_error)}")
                raise count_error
                
        except Exception as e:
            print(f"[VERBOSE] Chroma DB not found or corrupted, creating new vector store: {str(e)}")
            detector = Detect_and_Create_file_VStore()
            
            # Start background updates for continuous indexing
            vs = detector.run_pipeline()
            detector.start_background_updates()
            
            # Store detector instance for future updates
            self.detector = detector
            
            return vs
    
    def get_all_tools(self) -> List:
        """Get all available tools."""
        # Create a closure for the search tool with vectorstore pre-bound
        @tool
        def search_files_tool(query: str) -> str:
            """Search files using semantic search engine."""
            try:
                results = self.vectorstore.similarity_search(query, k=10)
                result_summaries = [doc.page_content for doc in results]
                return "\n\n".join(result_summaries)
            except Exception as e:
                error_msg = f"Error searching files: {str(e)}"
                print(f"[VERBOSE] {error_msg}")
                return error_msg
        
        return [
            # self.shell_tool,
            self.file_management_tools[6],  # List directory tool
            open_file_tool,
            create_vector_store_and_query,
            search_files_tool,
            extract_image_text
        ]


def read_excel_file_safely(file_path: str) -> List[Document]:
    """Safely read Excel file with multiple fallback methods."""
    documents = []
    
    try:
        # Method 1: Try pandas with different engines
        if EXCEL_DEPS_AVAILABLE:
            print(f"[VERBOSE] Trying to read Excel file with pandas: {file_path}")
            
            # Try different engines in order of preference
            engines = ['openpyxl', 'xlrd', None]
            
            for engine in engines:
                try:
                    if engine:
                        df = pd.read_excel(file_path, engine=engine, sheet_name=None)  # Read all sheets
                    else:
                        df = pd.read_excel(file_path, sheet_name=None)  # Let pandas choose engine
                    
                    # Convert all sheets to text
                    all_content = []
                    for sheet_name, sheet_df in df.items():
                        sheet_content = f"Sheet: {sheet_name}\n"
                        sheet_content += sheet_df.to_string(index=False)
                        all_content.append(sheet_content)
                    
                    combined_content = "\n\n".join(all_content)
                    documents.append(Document(
                        page_content=combined_content,
                        metadata={"source": file_path, "type": "excel"}
                    ))
                    
                    print(f"[VERBOSE] Successfully read Excel file with engine: {engine}")
                    return documents
                    
                except Exception as e:
                    print(f"[VERBOSE] Failed with engine {engine}: {str(e)}")
                    continue
        
        # Method 2: Try UnstructuredExcelLoader as fallback
        print(f"[VERBOSE] Trying UnstructuredExcelLoader for: {file_path}")
        try:
            loader = UnstructuredExcelLoader(file_path)
            documents.extend(loader.load())
            print(f"[VERBOSE] Successfully read Excel file with UnstructuredExcelLoader")
            return documents
        except Exception as e:
            print(f"[VERBOSE] UnstructuredExcelLoader failed: {str(e)}")
        
        # Method 3: Try to read as CSV if it's a simple format
        print(f"[VERBOSE] Trying to read as CSV: {file_path}")
        try:
            if EXCEL_DEPS_AVAILABLE:
                df = pd.read_csv(file_path)
                content = df.to_string(index=False)
                documents.append(Document(
                    page_content=content,
                    metadata={"source": file_path, "type": "csv_fallback"}
                ))
                print(f"[VERBOSE] Successfully read as CSV")
                return documents
        except Exception as e:
            print(f"[VERBOSE] CSV fallback failed: {str(e)}")
        
        # Method 4: Last resort - inform user about the limitation
        error_msg = (
            f"Unable to read Excel file '{os.path.basename(file_path)}'. "
            f"This might be due to:\n"
            f"1. File encryption/password protection\n"
            f"2. Corrupted file format\n"
            f"3. Missing required dependencies\n"
            f"4. Unsupported Excel version\n\n"
            f"Suggestions:\n"
            f"- Try saving the file as .csv format\n"
            f"- Remove password protection if any\n"
            f"- Use a different Excel file format (.xlsx instead of .xls or vice versa)"
        )
        
        documents.append(Document(
            page_content=error_msg,
            metadata={"source": file_path, "type": "error", "error": "read_failed"}
        ))
        
        return documents
        
    except Exception as e:
        error_msg = f"Critical error reading Excel file: {str(e)}"
        print(f"[VERBOSE] {error_msg}")
        documents.append(Document(
            page_content=error_msg,
            metadata={"source": file_path, "type": "critical_error"}
        ))
        return documents


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
        success_msg = f'The file "{os.path.basename(file_path)}" has been successfully opened. If you need any further assistance, feel free to ask!'
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
        file_extension = file_path.lower()
        
        if file_extension.endswith('.pdf'):
            loader = PyMuPDFLoader(file_path)
            documents.extend(loader.load())
        elif file_extension.endswith('.docx'):
            loader = Docx2txtLoader(file_path)
            documents.extend(loader.load())
        elif file_extension.endswith(('.xlsx', '.xls')):
            # Use our safe Excel reader
            documents.extend(read_excel_file_safely(file_path))
        elif file_extension.endswith('.pptx'):
            loader = UnstructuredPowerPointLoader(file_path)
            documents.extend(loader.load())
        else:
            # Handle text files and other formats
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append(Document(page_content=content))
            except UnicodeDecodeError:
                # Try different encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        with open(file_path, "r", encoding=encoding) as f:
                            content = f.read()
                            documents.append(Document(page_content=content))
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return f"Unable to read file due to encoding issues: {file_path}"
        
        if not documents:
            return f"No content could be extracted from the file: {file_path}"
        
        # Create an in-memory Chroma instance
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY"))
        vector_store = Chroma(
            collection_name="my_in_memory_collection",
            embedding_function=embeddings,
        )
        vector_store.add_documents(documents)

        results = vector_store.similarity_search(query, k=5)

        # Process the results
        if not results:
            return f"No relevant content found for query '{query}' in file {os.path.basename(file_path)}"
        
        result_summaries = []
        for i, doc in enumerate(results, 1):
            content = doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content
            result_summaries.append(f"Result {i}:\n{content}")
        
        return "\n\n".join(result_summaries)
        
    except Exception as e:
        error_msg = f"Error creating vector store and querying file: {str(e)}"
        print(f"[VERBOSE] {error_msg}")
        return error_msg
    
# @tool
# def list_directory(directory_path: str, required_extension_file: List[str]) -> List[str]:
#     """
#     Lists all files in the specified directory and subdirectories.

#     Args:
#         directory_path (str): The path to the directory to scan.
#         required_extension_file: Required file extension (e.g., .txt, .pdf,)

#     Returns:
#         list: A list of full file paths (strings) matching the criteria with allowed extension and without extension are folders.
#     """
#     print(f"[VERBOSE] Listing files in directory: {directory_path} with extensions: {required_extension_file}")
#     toolkit = FileManagementToolkit()
#     file_management_tools = toolkit.get_tools()
#     list_dir = file_management_tools[6]  # Assuming the 7th tool is the list directory tool
#     result = list_dir.invoke(input=directory_path)
#     result= result.split("\n")
#     print(f"[VERBOSE] Raw list directory result: {result}")
#     # allowed_extensions = ('.pdf', '.ppt', '.pptx', '.xls', '.xlsx','.csv', '.doc', '.docx', '.jpg', '.jpeg', '.png')
#     allowed_extensions = tuple(required_extension_file)
    
#     filtered_files = []
    
#     # Walk through only the specified directory with subdirectories
#     for file in result:
#         if (os.path.isfile(file) and file.lower().endswith(allowed_extensions)) or os.path.isdir(file):
#             filtered_files.append(file)
#             if os.path.isdir(file):
#                 # If it's a directory, list its contents (limited to 50 files)
#                 file_count = 0
#                 for root, dirs, files in os.walk(file):
#                     for f in files:
#                         if f.lower().endswith(allowed_extensions):
#                             filtered_files.append(os.path.join(root, f))
#                             file_count += 1
#                             if file_count >= 50:
#                                 break
#                     if file_count >= 50:
#                         break

#     # # Walk through directory and all subdirectories
#     # for root, dirs, files in os.walk(directory_path):
#     #     for i,file in enumerate(files):
#     #         if file.lower().endswith(allowed_extensions):
#     #             if i==0:
#     #                 filtered_files.append(os.path.join(root, file))
#     #             else:
#     #                 filtered_files.append(os.path.join(file))
#     print(f"[VERBOSE] Filtered files: {filtered_files}")
#     return filtered_files

# @tool 
# def search_file(query:str)->str:
#     """Search files using Everything Search Engine API. """
#     url = f"http://127.0.0.1:8888/?s={query}&json=1&path_column=1"  # add json=1 to get JSON response
#     resp = requests.get(url)
#     # print(resp)
#     resp.raise_for_status()
#     file_paths = resp.json()
#     print(file_paths)  # parse JSON response
#     search_results = ''
#     for file in file_paths['results']: 
#         search_results += f"{file['path']+'\\'+file['name']} ;"
#     print(search_results)
#     return search_results

@tool
def extract_image_text(image_path: str) -> str:
    """Extract text from an image file using OCR."""
    try:
        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            return f"File does not exist: {image_path}"
        
        # Finding image extension
        image_filename, image_extension = os.path.splitext(image_path)
        image_extension = image_extension.lower().replace('.', '')

        # Adding images encoding as tool
        with open(image_path, "rb") as image_file:
            encoding = base64.b64encode(image_file.read()).decode('utf-8')

        # Initialize the OpenAI multimodal model
        llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=1024)

        # Create the message payload for the chat model
        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Extract all the text from this image and list it clearly."
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{image_extension};base64,{encoding}"},
                },
            ]
        )

        # Invoke the model
        response = llm.invoke([message])

        return response.content
    except Exception as e:
        error_msg = f"Error extracting text from image {image_path}: {str(e)}"
        print(f"[VERBOSE] {error_msg}")
        return error_msg


def get_file_tools(root_dir: str = "C:\\") -> List:
    """Factory function to get file tools."""
    file_tools = FileTools(root_dir)
    return file_tools.get_all_tools()