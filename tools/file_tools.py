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
from utils.sementic_search_engine import Detect_and_Create_file_VStore, get_cached_hf_embeddings, clear_global_hf_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add HuggingFace embeddings support
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    HF_EMBEDDINGS_AVAILABLE = True
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        HF_EMBEDDINGS_AVAILABLE = True
    except ImportError:
        HF_EMBEDDINGS_AVAILABLE = False
        print("[WARNING] HuggingFace embeddings not available. Install: pip install sentence-transformers")

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
    
    def __init__(self, root_dir: str = "C:\\", use_hf_embeddings: bool = True):
        self.root_dir = root_dir
        self.use_hf_embeddings = use_hf_embeddings
        self.shell_tool = ShellTool()
        self.toolkit = FileManagementToolkit(root_dir=self.root_dir)
        self.file_management_tools = self.toolkit.get_tools()
        self.vectorstore = self.get_vectorstore()
        
        # Session-based document vectorstores (persistent)
        self.document_vectorstores = {}  # {file_path: vectorstore}
        self.session_persist_dir = "./session_vectorstores"
        os.makedirs(self.session_persist_dir, exist_ok=True)

    def get_hf_embeddings(self):
        """Get HuggingFace embeddings model with global caching."""
        return get_cached_hf_embeddings()
    
    @classmethod
    def clear_hf_cache(cls):
        """Clear the cached HuggingFace embeddings model."""
        clear_global_hf_cache()
    
    @classmethod
    def get_cache_info(cls):
        """Get information about the cached model."""
        from utils.sementic_search_engine import _GLOBAL_HF_MODEL_NAME, _GLOBAL_HF_EMBEDDINGS_CACHE
        
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "local_filesearch_agent")
        cache_exists = os.path.exists(cache_dir)
        model_cached = _GLOBAL_HF_EMBEDDINGS_CACHE is not None
        
        return {
            "model_name": _GLOBAL_HF_MODEL_NAME,
            "cache_directory": cache_dir,
            "cache_directory_exists": cache_exists,
            "model_in_memory": model_cached
        }

    def get_vectorstore(self):
        """Get or create vectorstore with proper cleanup to avoid lock issues."""
        chroma_instance = None
        
        try:
            # Choose embedding based on configuration
            if self.use_hf_embeddings and HF_EMBEDDINGS_AVAILABLE:
                embeddings = self.get_hf_embeddings()
                print("[VERBOSE] Using HuggingFace embeddings")
            else:
                embeddings = OpenAIEmbeddings()
                print("[VERBOSE] Using OpenAI embeddings")
            
            # Check if database directory and metadata exist
            db_exists = os.path.exists("./chroma_db")
            metadata_exists = os.path.exists("./file_metadata.json")
            
            print(f"[VERBOSE] Database check - DB exists: {db_exists}, Metadata exists: {metadata_exists}")
            
            # Only try to open if both exist
            if db_exists and metadata_exists:
                try:
                    # Try to open existing vectorstore
                    chroma_instance = Chroma(
                        collection_name="paths", 
                        embedding_function=embeddings, 
                        persist_directory="./chroma_db"
                    )
                    
                    # Verify the vectorstore has content
                    collection_count = chroma_instance._collection.count()
                    
                    print(f"[VERBOSE] Existing vectorstore found with {collection_count:,} documents")
                    
                    # Only rebuild if truly empty (less than 10 documents is suspicious)
                    if collection_count < 10:
                        print("[VERBOSE] Vectorstore has very few documents, checking metadata...")
                        
                        # Check metadata to decide
                        try:
                            with open("./file_metadata.json", 'r') as f:
                                import json
                                metadata = json.load(f)
                                metadata_count = len(metadata)
                            
                            print(f"[VERBOSE] Metadata shows {metadata_count:,} files should be indexed")
                            
                            # If metadata has many files but vectorstore is empty, it's corrupted
                            if metadata_count > 100 and collection_count < 10:
                                print("[WARNING] Vectorstore appears corrupted (metadata mismatch)")
                                raise Exception("Corrupted vectorstore - metadata mismatch")
                            elif collection_count == 0:
                                print("[WARNING] Vectorstore is completely empty")
                                raise Exception("Empty vectorstore")
                        except FileNotFoundError:
                            print("[WARNING] Metadata file not found")
                            raise Exception("Missing metadata file")
                    
                    # Vectorstore is valid and has content - just return it!
                    print(f"[OK] ✅ Using existing vectorstore with {collection_count:,} documents")
                    print(f"[OK] 🚀 No rebuild needed - vectorstore is ready!")
                    self.vectorstore = chroma_instance
                    return chroma_instance
                    
                except Exception as verify_error:
                    print(f"[VERBOSE] Vectorstore verification failed: {str(verify_error)}")
                    
                    # Close this instance before rebuilding
                    if chroma_instance:
                        del chroma_instance
                        chroma_instance = None
                    
                    # Force cleanup
                    import gc
                    gc.collect()
                    import time
                    time.sleep(1)
                    
                    # Re-raise to trigger rebuild
                    raise verify_error
            else:
                print("[VERBOSE] Database or metadata missing - need to create new vectorstore")
                raise Exception("Database files not found")
                
        except Exception as e:
            print(f"[VERBOSE] Need to create/rebuild vectorstore: {str(e)}")
            
            # Make sure any open instance is closed
            if chroma_instance:
                del chroma_instance
                chroma_instance = None
            
            # Force cleanup
            import gc
            import time
            gc.collect()
            time.sleep(1)
            
            # Now create the detector and run pipeline
            print("[VERBOSE] Creating new vectorstore with file detector...")
            detector = Detect_and_Create_file_VStore(use_hf_embeddings=self.use_hf_embeddings)
            
            # The detector will handle whether to do full rebuild or incremental
            vs = detector.run_pipeline()
            detector.start_background_updates()
            
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
        
        # Create document query tool with self bound
        @tool
        def query_document_tool(file_path: str, query: str) -> str:
            """Query a specific document that was previously indexed. You can use just the filename if only one document is indexed. For comprehensive answers about resumes/CVs, try broader queries."""
            return self.query_document(file_path, query)
        
        @tool
        def index_document_tool(file_path: str) -> str:
            """Index a document for querying. Call this first before querying a document. Returns the indexed document info."""
            return self.index_document(file_path)
        
        @tool
        def list_indexed_documents_tool() -> str:
            """List all documents currently indexed in this session. Use this to see what documents are available for querying."""
            return self.list_indexed_documents()
        
        @tool
        def get_full_document_content_tool(file_path: str) -> str:
            """Get the COMPLETE content of an indexed document. Use this for small documents like resumes when you need to see everything, not just search results."""
            return self.get_full_document_content(file_path)
        
        return [
            # self.shell_tool,
            self.file_management_tools[6],  # List directory tool
            open_file_tool,
            index_document_tool,  # New: Index document
            query_document_tool,  # New: Query indexed document
            list_indexed_documents_tool,  # New: List indexed documents
            get_full_document_content_tool,  # New: Get complete document
            search_files_tool,
            extract_image_text
        ]
    
    def list_indexed_documents(self) -> str:
        """List all documents currently indexed in this session.
        
        Returns:
            List of indexed documents with details
        """
        if not self.document_vectorstores:
            return "📋 No documents are currently indexed.\n\n💡 Use the index_document tool to index a document first."
        
        result = f"📋 Currently indexed documents ({len(self.document_vectorstores)}):\n\n"
        
        for i, (file_path, vs_info) in enumerate(self.document_vectorstores.items(), 1):
            filename = os.path.basename(file_path)
            doc_count = vs_info['doc_count']
            result += f"{i}. **{filename}**\n"
            result += f"   📁 Path: {file_path}\n"
            result += f"   📊 Chunks: {doc_count}\n"
            result += f"   ✅ Ready for querying\n\n"
        
        result += "💡 To query any of these documents, use:\n"
        result += "   query_document(filename, your_question)\n"
        result += "   or\n"
        result += "   query_document(full_path, your_question)"
        
        return result
    
    def get_full_document_content(self, file_path: str) -> str:
        """Get the complete content of an indexed document.
        
        Useful for small documents like resumes where you want to see everything.
        
        Args:
            file_path: Full path or filename of the indexed document
            
        Returns:
            Complete document content
        """
        try:
            # Smart file path matching (same as query_document)
            if not os.path.isabs(file_path) and len(self.document_vectorstores) > 0:
                filename_lower = os.path.basename(file_path).lower()
                matched_paths = [p for p in self.document_vectorstores.keys() 
                                if os.path.basename(p).lower() == filename_lower]
                
                if len(matched_paths) == 1:
                    file_path = matched_paths[0]
                elif len(matched_paths) == 0 and len(self.document_vectorstores) == 1:
                    file_path = list(self.document_vectorstores.keys())[0]
            
            # Check if document is indexed
            if file_path not in self.document_vectorstores:
                return (
                    f"❌ Document '{os.path.basename(file_path)}' is not indexed.\n"
                    f"💡 Use index_document first."
                )
            
            print(f"[VERBOSE] Getting full content of: {file_path}")
            
            # Get vectorstore
            vs_info = self.document_vectorstores[file_path]
            vectorstore = vs_info['vectorstore']
            
            # Get ALL documents from vectorstore (no similarity search, just retrieve all)
            # Use a dummy search to get all documents, or access the collection directly
            try:
                # Get all documents by searching with empty query and high k
                all_results = vectorstore.similarity_search("", k=100)
                
                if not all_results:
                    # Fallback: get from collection directly
                    collection = vectorstore._collection
                    all_data = collection.get()
                    
                    if all_data and 'documents' in all_data:
                        full_content = "\n\n---\n\n".join(all_data['documents'])
                    else:
                        return "❌ Could not retrieve document content"
                else:
                    # Combine all chunks
                    full_content = "\n\n---\n\n".join([doc.page_content for doc in all_results])
                
                print(f"[VERBOSE] Retrieved complete content ({len(full_content)} characters)")
                
                # Limit output to reasonable size (100KB max)
                max_chars = 100000
                if len(full_content) > max_chars:
                    full_content = full_content[:max_chars] + f"\n\n... (truncated, showing first {max_chars} characters)"
                
                return (
                    f"📖 Complete content of '{os.path.basename(file_path)}':\n"
                    f"{'=' * 70}\n\n"
                    f"{full_content}\n\n"
                    f"{'=' * 70}\n"
                    f"✅ End of document"
                )
                
            except Exception as e:
                print(f"[VERBOSE] Error retrieving full content: {e}")
                return f"❌ Error retrieving full content: {str(e)}"
                
        except Exception as e:
            error_msg = f"❌ Error getting document content: {str(e)}"
            print(f"[VERBOSE] {error_msg}")
            return error_msg
    
    def index_document(self, file_path: str) -> str:
        """Index a document for persistent querying throughout the session.
        
        Args:
            file_path: Full path to the document
            
        Returns:
            Success/error message
        """
        try:
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                return f"❌ File does not exist: {file_path}"
            
            # Check if already indexed
            if file_path in self.document_vectorstores:
                return f"✅ Document '{os.path.basename(file_path)}' is already indexed and ready for querying."
            
            print(f"[VERBOSE] Indexing document: {file_path}")
            
            # Load document based on type
            documents = []
            file_extension = file_path.lower()
            
            if file_extension.endswith('.pdf'):
                # Try to load PDF with text extraction first
                loader = PyMuPDFLoader(file_path)
                raw_docs = loader.load()
                
                # Check if PDF has extractable text or if it's image-based/scanned
                total_text = "".join([doc.page_content for doc in raw_docs])
                is_scanned = len(total_text.strip()) < 100  # Very little text = likely scanned
                
                if is_scanned:
                    print(f"[VERBOSE] Detected scanned/image-based PDF - extracting images and using OCR")
                    
                    # Extract images from PDF and use OCR
                    try:
                        import fitz  # PyMuPDF
                        pdf_document = fitz.open(file_path)
                        ocr_texts = []
                        
                        for page_num in range(len(pdf_document)):
                            page = pdf_document[page_num]
                            image_list = page.get_images()
                            
                            if image_list:
                                print(f"[VERBOSE] Page {page_num + 1}: Found {len(image_list)} images")
                                
                                for img_index, img_info in enumerate(image_list):
                                    xref = img_info[0]
                                    base_image = pdf_document.extract_image(xref)
                                    image_bytes = base_image["image"]
                                    
                                    # Save image temporarily
                                    import tempfile
                                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img:
                                        temp_img.write(image_bytes)
                                        temp_img_path = temp_img.name
                                    
                                    # Use OCR to extract text from image
                                    print(f"[VERBOSE] Extracting text from image {img_index + 1} on page {page_num + 1}")
                                    ocr_text = extract_image_text(temp_img_path)
                                    
                                    if ocr_text and not ocr_text.startswith("Error"):
                                        ocr_texts.append(f"[Page {page_num + 1}, Image {img_index + 1}]\n{ocr_text}")
                                    
                                    # Clean up temp file
                                    try:
                                        os.unlink(temp_img_path)
                                    except:
                                        pass
                        
                        pdf_document.close()
                        
                        if ocr_texts:
                            # Create documents from OCR text
                            combined_ocr = "\n\n---\n\n".join(ocr_texts)
                            documents = [Document(
                                page_content=combined_ocr,
                                metadata={"source": file_path, "type": "scanned_pdf_with_ocr"}
                            )]
                            print(f"[VERBOSE] Successfully extracted text from {len(ocr_texts)} images using OCR")
                        else:
                            print(f"[VERBOSE] No images found or OCR failed, using original text")
                            documents = raw_docs
                            
                    except Exception as ocr_error:
                        print(f"[VERBOSE] OCR extraction failed: {ocr_error}")
                        print(f"[VERBOSE] Falling back to original text extraction")
                        documents = raw_docs
                else:
                    print(f"[VERBOSE] PDF has text content - using standard extraction")
                    
                    # For resumes/small PDFs, use text splitting for better chunking
                    if len(raw_docs) <= 5:  # Small document like a resume
                        from langchain.text_splitter import RecursiveCharacterTextSplitter
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=800,  # Smaller chunks for better search
                            chunk_overlap=200,  # Good overlap to maintain context
                            length_function=len,
                            separators=["\n\n", "\n", ". ", " ", ""]
                        )
                        documents = text_splitter.split_documents(raw_docs)
                        print(f"[VERBOSE] Split PDF into {len(documents)} chunks (was {len(raw_docs)} pages)")
                    else:
                        # Large document, use pages as-is
                        documents.extend(raw_docs)
                        print(f"[VERBOSE] Using {len(documents)} pages from PDF")
                    
            elif file_extension.endswith('.docx'):
                loader = Docx2txtLoader(file_path)
                documents.extend(loader.load())
            elif file_extension.endswith(('.xlsx', '.xls')):
                documents.extend(read_excel_file_safely(file_path))
            elif file_extension.endswith('.pptx'):
                loader = UnstructuredPowerPointLoader(file_path)
                documents.extend(loader.load())
            else:
                # Handle text files
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        documents.append(Document(page_content=content, metadata={"source": file_path}))
                except UnicodeDecodeError:
                    # Try different encodings
                    for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            with open(file_path, "r", encoding=encoding) as f:
                                content = f.read()
                                documents.append(Document(page_content=content, metadata={"source": file_path}))
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        return f"❌ Unable to read file due to encoding issues: {file_path}"
            
            if not documents:
                return f"❌ No content could be extracted from: {file_path}"
            
            # Create persistent vectorstore for this document
            import hashlib
            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
            persist_path = os.path.join(self.session_persist_dir, f"doc_{file_hash}")
            
            print(f"[VERBOSE] Creating persistent vectorstore at: {persist_path}")
            
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY"))
            vectorstore = Chroma(
                collection_name=f"doc_{file_hash}",
                embedding_function=embeddings,
                persist_directory=persist_path
            )
            vectorstore.add_documents(documents)
            
            # Store in session
            self.document_vectorstores[file_path] = {
                'vectorstore': vectorstore,
                'persist_path': persist_path,
                'doc_count': len(documents)
            }
            
            print(f"[VERBOSE] Successfully indexed {len(documents)} document chunks")
            
            return (
                f"✅ Successfully indexed '{os.path.basename(file_path)}'!\n\n"
                f"📁 **Full path**: {file_path}\n"
                f"📊 Processed: {len(documents)} document chunks\n"
                f"✅ Status: Ready for querying\n\n"
                f"💡 To query this document, use:\n"
                f"   query_document(\"{file_path}\", \"your question\")\n"
                f"   OR simply:\n"
                f"   query_document(\"{os.path.basename(file_path)}\", \"your question\")\n\n"
                f"🔄 This document stays indexed for the entire session - no need to re-index!"
            )
            
        except Exception as e:
            error_msg = f"❌ Error indexing document: {str(e)}"
            print(f"[VERBOSE] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg
    
    def query_document(self, file_path: str, query: str) -> str:
        """Query a previously indexed document.
        
        Args:
            file_path: Full path to the document (or just filename if only one document indexed)
            query: Question to ask about the document
            
        Returns:
            Answer based on document content
        """
        try:
            # Smart file path matching - if only filename provided, try to find full path
            if not os.path.isabs(file_path) and len(self.document_vectorstores) > 0:
                # User provided just filename, try to match with indexed documents
                filename_lower = os.path.basename(file_path).lower()
                
                matched_paths = []
                for indexed_path in self.document_vectorstores.keys():
                    if os.path.basename(indexed_path).lower() == filename_lower:
                        matched_paths.append(indexed_path)
                
                if len(matched_paths) == 1:
                    file_path = matched_paths[0]
                    print(f"[VERBOSE] Matched filename to: {file_path}")
                elif len(matched_paths) > 1:
                    return (
                        f"❌ Multiple documents with name '{file_path}' are indexed:\n" +
                        "\n".join([f"  - {p}" for p in matched_paths]) +
                        "\n\n💡 Please specify the full path."
                    )
                else:
                    # No match found, check if there's only one indexed document
                    if len(self.document_vectorstores) == 1:
                        file_path = list(self.document_vectorstores.keys())[0]
                        print(f"[VERBOSE] Using the only indexed document: {file_path}")
                    else:
                        return (
                            f"❌ Document '{file_path}' not found in indexed documents.\n"
                            f"📋 Currently indexed documents:\n" +
                            "\n".join([f"  - {os.path.basename(p)}" for p in self.document_vectorstores.keys()]) +
                            "\n\n💡 Please use the exact filename or full path."
                        )
            
            # Check if document is indexed
            if file_path not in self.document_vectorstores:
                return (
                    f"❌ Document '{os.path.basename(file_path)}' is not indexed yet.\n"
                    f"📋 Currently indexed documents:\n" +
                    "\n".join([f"  - {os.path.basename(p)}" for p in self.document_vectorstores.keys()]) +
                    f"\n\n💡 Please use the index_document tool first to index this document."
                )
            
            print(f"[VERBOSE] Querying document: {file_path}")
            print(f"[VERBOSE] Query: {query}")
            
            # Get vectorstore
            vs_info = self.document_vectorstores[file_path]
            vectorstore = vs_info['vectorstore']
            
            # Smart query handling - detect counting questions
            query_lower = query.lower()
            is_counting_query = any(word in query_lower for word in ['how many', 'count', 'total', 'number of', 'how much'])
            
            # For Excel files, always fetch more context
            file_ext = os.path.splitext(file_path)[1].lower()
            is_excel = file_ext in ['.xlsx', '.xls', '.csv']
            
            # Adjust search parameters based on query type
            if is_counting_query or is_excel:
                # For counting queries or Excel files, get more results to ensure we capture summary info
                k = 15
                print(f"[VERBOSE] Detected {'counting query' if is_counting_query else 'Excel file'} - fetching {k} chunks")
            else:
                k = 10
            
            # Perform similarity search
            results = vectorstore.similarity_search(query, k=k)
            
            if not results:
                return f"❌ No relevant content found for query: '{query}'"
            
            # ENHANCED: Check if summary section is in results (for Excel files)
            summary_found = False
            for doc in results:
                if "EXCEL FILE SUMMARY" in doc.page_content or "Total Data Rows" in doc.page_content:
                    summary_found = True
                    break
            
            # Format results intelligently
            result_summaries = []
            for i, doc in enumerate(results, 1):
                content = doc.page_content
                
                # For counting queries, prioritize showing summary and metadata
                if is_counting_query and ("SUMMARY" in content or "Rows:" in content or "Total" in content):
                    # Show full content for summary sections
                    result_summaries.insert(0, f"📊 KEY INFO:\n{content}")
                else:
                    # Show truncated content for other sections
                    max_len = 800 if is_excel else 1000
                    truncated = content[:max_len] + "..." if len(content) > max_len else content
                    result_summaries.append(f"📄 Section {i}:\n{truncated}")
            
            # Build response with smart hints
            response = f"📖 Query: '{query}'\n"
            response += f"📁 Document: '{os.path.basename(file_path)}'\n"
            response += f"🔍 Found {len(results)} relevant sections\n\n"
            
            # Add helpful context for counting queries
            if is_counting_query and is_excel:
                response += "💡 TIP: Look for 'Total Rows', 'Rows:', or count numbers in the data below:\n\n"
            
            response += "\n\n".join(result_summaries[:10])  # Limit to top 10 for readability
            
            print(f"[VERBOSE] Returned {len(results)} results from {file_path} (counting query: {is_counting_query})")
            
            return response
            
        except Exception as e:
            error_msg = f"❌ Error querying document: {str(e)}"
            print(f"[VERBOSE] {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg
    
    def cleanup_session_vectorstores(self):
        """Clean up all session-based vectorstores when session ends."""
        try:
            print("[VERBOSE] Cleaning up session vectorstores...")
            
            # Close all vectorstores
            for file_path, vs_info in self.document_vectorstores.items():
                try:
                    vectorstore = vs_info.get('vectorstore')
                    if vectorstore:
                        # Try to properly close the vectorstore
                        try:
                            if hasattr(vectorstore, '_client'):
                                vectorstore._client = None
                            if hasattr(vectorstore, '_collection'):
                                vectorstore._collection = None
                        except:
                            pass
                        del vs_info['vectorstore']
                except Exception as e:
                    print(f"[VERBOSE] Error closing vectorstore for {file_path}: {e}")
            
            self.document_vectorstores.clear()
            
            # Force garbage collection multiple times
            import gc
            gc.collect()
            gc.collect()
            
            # Wait longer for file handles to release on Windows
            import time
            time.sleep(2)
            
            # Delete the session directory with retry logic
            if os.path.exists(self.session_persist_dir):
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        import shutil
                        shutil.rmtree(self.session_persist_dir, ignore_errors=True)
                        print(f"[VERBOSE] ✅ Cleaned up session vectorstores")
                        break
                    except PermissionError as e:
                        if attempt < max_retries - 1:
                            print(f"[VERBOSE] Retry {attempt + 1}/{max_retries} - waiting for file handles...")
                            time.sleep(1)
                            gc.collect()
                        else:
                            print(f"[VERBOSE] ⚠️ Could not delete session directory after {max_retries} attempts: {e}")
                    except Exception as e:
                        print(f"[VERBOSE] ⚠️ Could not delete session directory: {e}")
                        break
            
        except Exception as e:
            # Silently handle cleanup errors - don't show scary error messages
            if "WinError 6" not in str(e):  # Only log non-handle errors
                print(f"[VERBOSE] Cleanup completed with minor issues: {e}")
    
    def __del__(self):
        """Cleanup when FileTools instance is destroyed."""
        try:
            self.cleanup_session_vectorstores()
        except Exception as e:
            # Silently handle - object is being destroyed anyway
            if "WinError 6" not in str(e):
                pass  # Ignore Windows handle errors during destruction


def read_excel_file_safely(file_path: str) -> List[Document]:
    """Safely read Excel file with multiple fallback methods and preserve structure for better querying."""
    documents = []
    
    try:
        # Method 1: Try pandas with different engines - IMPROVED for better structure
        if EXCEL_DEPS_AVAILABLE:
            print(f"[VERBOSE] Trying to read Excel file with pandas: {file_path}")
            
            # Try different engines in order of preference
            engines = ['openpyxl', 'xlrd', None]
            
            for engine in engines:
                try:
                    if engine:
                        df_dict = pd.read_excel(file_path, engine=engine, sheet_name=None)  # Read all sheets
                    else:
                        df_dict = pd.read_excel(file_path, sheet_name=None)  # Let pandas choose engine
                    
                    # Convert all sheets to text with ENHANCED METADATA
                    all_content = []
                    
                    # Add file summary at the top
                    summary = f"📊 EXCEL FILE SUMMARY: {os.path.basename(file_path)}\n"
                    summary += f"Total Sheets: {len(df_dict)}\n"
                    total_rows = sum(len(df) for df in df_dict.values())
                    summary += f"Total Data Rows (all sheets): {total_rows}\n\n"
                    all_content.append(summary)
                    
                    for sheet_name, sheet_df in df_dict.items():
                        # Remove completely empty rows
                        sheet_df = sheet_df.dropna(how='all')
                        
                        # Sheet header with metadata
                        sheet_content = f"{'='*60}\n"
                        sheet_content += f"📋 SHEET: {sheet_name}\n"
                        sheet_content += f"Rows: {len(sheet_df)} | Columns: {len(sheet_df.columns)}\n"
                        sheet_content += f"{'='*60}\n\n"
                        
                        # Column names
                        sheet_content += f"COLUMNS: {', '.join(str(col) for col in sheet_df.columns)}\n\n"
                        
                        # Data with row numbers for counting
                        if len(sheet_df) > 0:
                            sheet_content += f"DATA (showing all {len(sheet_df)} rows):\n"
                            # Convert to string with better formatting
                            sheet_content += sheet_df.to_string(index=True, max_rows=None)
                        else:
                            sheet_content += "(No data in this sheet)\n"
                        
                        all_content.append(sheet_content)
                    
                    combined_content = "\n\n".join(all_content)
                    documents.append(Document(
                        page_content=combined_content,
                        metadata={
                            "source": file_path, 
                            "type": "excel",
                            "total_sheets": len(df_dict),
                            "total_rows": total_rows,
                            "engine": engine or "default"
                        }
                    ))
                    
                    print(f"[VERBOSE] Successfully read Excel file with engine: {engine} ({total_rows} total rows)")
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

# DEPRECATED: This function is replaced by index_document and query_document
# Keeping for backwards compatibility but not recommended
@tool
def create_vector_store_and_query(file_path: str, query: str) -> str:
    """[DEPRECATED] Create a vector store from files path given and query it.
    
    ⚠️ This tool is deprecated. Use index_document first, then query_document instead.
    This creates a temporary vectorstore that only works once.
    """
    return (
        "⚠️ This tool is deprecated and may not work reliably.\n\n"
        "Please use the new workflow:\n"
        "1. First call: index_document(file_path) - to index the document\n"
        "2. Then call: query_document(file_path, query) - to ask questions\n\n"
        "The new approach creates a persistent vectorstore that works for multiple queries."
    )
    
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