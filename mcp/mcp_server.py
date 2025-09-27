from fastmcp import FastMCP
import base64
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


mcp = FastMCP("My MCP Server")
@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

@mcp.tool
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

@mcp.tool
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
        elif file_path.lower().endswith('.pptx'):
            loader = UnstructuredPowerPointLoader(file_path)
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
        result_summaries = [doc.page_content[:500] + "..." for doc in results]
        return "\n\n".join(result_summaries)
        # Save the vector store to a persistent location if needed
        # vector_store.persist("path_to_persist_vector_store")
        
    except Exception as e:
        error_msg = f"Error creating vector store : {str(e)}"
        print(f"[VERBOSE] {error_msg}")
        return error_msg
    

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

@mcp.tool
def extract_image_text(image_path: str) -> str:
    """Extract text from an image file using OCR."""
    try:
        if not os.path.exists(image_path) or not os.path.isfile(image_path):
            return f"File does not exist: {image_path}"
        
        ## finding image extension
        image_filename, image_extension = os.path.splitext(image_path)
        image_extension = image_extension.lower()

        ## adding images encoding as tool
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

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)