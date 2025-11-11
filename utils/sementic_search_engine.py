# Updated pipeline cell: detect drives, gather file paths, remove existing chroma db, create/retry Chroma vectorstore
import os
import time
import shutil
import logging
import psutil
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

# Load environment variables and HuggingFace support
load_dotenv()

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    HF_EMBEDDINGS_AVAILABLE = True
except ImportError:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        HF_EMBEDDINGS_AVAILABLE = True
    except ImportError:
        HF_EMBEDDINGS_AVAILABLE = False

import torch

logging.basicConfig(level=logging.INFO)

# Global cache for HuggingFace embeddings to avoid re-downloading
_GLOBAL_HF_EMBEDDINGS_CACHE = None
_GLOBAL_HF_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

def get_cached_hf_embeddings():
    """Get cached HuggingFace embeddings with GPU optimization."""
    global _GLOBAL_HF_EMBEDDINGS_CACHE
    
    if _GLOBAL_HF_EMBEDDINGS_CACHE is not None:
        print("✅ Using cached HuggingFace embeddings model")
        return _GLOBAL_HF_EMBEDDINGS_CACHE
    
    try:
        print("📥 Loading HuggingFace model with optimizations...")
        
        # This model is public and doesn't need authentication
        # Remove any HF_TOKEN from environment to avoid authentication errors
        if "HF_TOKEN" in os.environ:
            del os.environ["HF_TOKEN"]
            print("🔓 Removed HF_TOKEN - using public model without authentication")
        
        # Create cache directory for models
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "local_filesearch_agent")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Check GPU availability
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Model configuration for optimization
        model_kwargs = {'device': device}
        
        if device == 'cuda':
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"🚀 GPU detected: {gpu_name} ({gpu_memory:.1f} GB)")
            
            # Use float16 for 2x speed boost on GPU
            try:
                model_kwargs['torch_dtype'] = torch.float16
                print("⚡ Using FP16 precision for 2x speed boost")
            except:
                print("⚠️  FP16 not available, using FP32")
        else:
            print(f"💻 Using CPU (no GPU detected)")
        
        # Encoding configuration with optimized batch size
        encode_kwargs = {
            'normalize_embeddings': True,
            # Note: Don't set show_progress_bar here - let it use default to avoid conflicts
        }
        
        # Optimize batch size based on device
        if device == 'cuda':
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            if gpu_memory > 8:
                encode_kwargs['batch_size'] = 512  # Large GPU
            elif gpu_memory > 4:
                encode_kwargs['batch_size'] = 256  # Medium GPU
            else:
                encode_kwargs['batch_size'] = 128  # Small GPU
        else:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            encode_kwargs['batch_size'] = min(cpu_count * 4, 64)  # CPU
        
        print(f"📊 Encoding batch size: {encode_kwargs['batch_size']}")
        
        embeddings = HuggingFaceEmbeddings(
            model_name=_GLOBAL_HF_MODEL_NAME,
            cache_folder=cache_dir,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
        
        # Cache the embeddings instance
        _GLOBAL_HF_EMBEDDINGS_CACHE = embeddings
        print(f"✅ Successfully loaded model: {_GLOBAL_HF_MODEL_NAME}")
        print(f"📁 Model cached in: {cache_dir}")
        
        return embeddings
        
    except Exception as e:
        print(f"❌ Failed to load HuggingFace embeddings: {e}")
        print("🔄 Falling back to OpenAI embeddings")
        return OpenAIEmbeddings()

def clear_global_hf_cache():
    """Clear the global HuggingFace embeddings cache."""
    global _GLOBAL_HF_EMBEDDINGS_CACHE
    _GLOBAL_HF_EMBEDDINGS_CACHE = None
    print("Global HuggingFace embeddings cache cleared")

class Detect_and_Create_file_VStore:
    """Detect drives, find files by extension and create a Chroma vectorstore.
       Supports incremental updates, periodic background scanning, batching, and parallelization."""
    ALLOWED_EXTS = ('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.ppt', '.pptx', '.xls', '.xlsx', '.csv')
    EXCLUDE_DIRS = ["Windows", "Program Files", "Program Files (x86)", "PerfLogs", "$Recycle.Bin",
                    "System Volume Information", "AppData", "Microsoft", "__pycache__", ".git", "node_modules"]

    def __init__(self, persist_directory="./chroma_db", metadata_file="./file_metadata.json", 
                 update_interval_hours=2, use_hf_embeddings=True, batch_size=2000, max_workers=4):
        self.persist_directory = persist_directory
        self.metadata_file = metadata_file
        self.update_interval_hours = update_interval_hours
        self.use_hf_embeddings = use_hf_embeddings
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.vectorstore = None
        self.file_metadata = self.load_metadata()
        self.background_thread = None
        self.stop_background = False
        
        # Initialize embeddings
        self.embeddings = self.get_embeddings()

    def get_embeddings(self):
        """Get embedding model (HuggingFace or OpenAI)."""
        if self.use_hf_embeddings and HF_EMBEDDINGS_AVAILABLE:
            return get_cached_hf_embeddings()
        else:
            print("Using OpenAI embeddings")
            return OpenAIEmbeddings()

    def load_metadata(self):
        """Load file metadata from JSON file."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load metadata file: {e}")
        return {}
    
    def save_metadata(self):
        """Save file metadata to JSON file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_metadata, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save metadata file: {e}")
    
    def get_file_info(self, file_path):
        """Get file modification time and size."""
        try:
            stat = os.stat(file_path)
            return {
                'mtime': stat.st_mtime,
                'size': stat.st_size,
                'last_indexed': time.time()
            }
        except (OSError, IOError):
            return None
    
    def is_file_modified(self, file_path):
        """Check if file has been modified since last indexing."""
        if file_path not in self.file_metadata:
            return True
        
        current_info = self.get_file_info(file_path)
        if not current_info:
            return False
            
        stored_info = self.file_metadata[file_path]
        return (current_info['mtime'] > stored_info.get('mtime', 0) or 
                current_info['size'] != stored_info.get('size', 0))

    def should_exclude(self, path):
        return any(excl.lower() in path.lower() for excl in self.EXCLUDE_DIRS)

    def find_files_by_extension_parallel(self, root_dirs, extensions=None, only_modified=False):
        """Find files by extension across multiple root directories in parallel."""
        extensions = extensions or self.ALLOWED_EXTS
        all_matched = []
        
        logging.info(f"Starting parallel file scan across {len(root_dirs)} root directories")
        logging.info(f"Using {self.max_workers} workers")
        
        def scan_single_root(root_path):
            """Scan a single root directory."""
            return self.find_files_by_extension(root_path, extensions, only_modified)
        
        # Use ThreadPoolExecutor for I/O bound file scanning
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all root directories for parallel processing
            future_to_root = {
                executor.submit(scan_single_root, root): root 
                for root in root_dirs
            }
            
            # Collect results as they complete
            for future in future_to_root:
                root = future_to_root[future]
                try:
                    matched_files = future.result()
                    logging.info(f"Completed scanning {root}: {len(matched_files)} files found")
                    all_matched.extend(matched_files)
                except Exception as e:
                    logging.error(f"Error scanning {root}: {e}")
        
        logging.info(f"Parallel scan completed: {len(all_matched)} total files found")
        return all_matched

    def find_files_by_extension(self, root_path, extensions=None, only_modified=False):
        """Find files by extension, optionally only modified files."""
        extensions = extensions or self.ALLOWED_EXTS
        matched = []
        new_files = []
        modified_files = []
        
        logging.info(f"Starting file scan in: {root_path}")
        
        def scan_dir(path, depth=0):
            if depth > 15:  # Prevent infinite recursion
                return
                
            try:
                entry_count = 0
                for entry in os.scandir(path):
                    entry_count += 1
                    if entry_count % 5000 == 0:  # Log progress every 5000 entries
                        logging.info(f"Processed {entry_count} entries in {path}")
                    
                    if entry.is_dir(follow_symlinks=False):
                        if not self.should_exclude(entry.path):
                            scan_dir(entry.path, depth + 1)
                    elif entry.is_file() and entry.name.lower().endswith(extensions):
                        if not (entry.name.startswith('~') or entry.name.startswith('.')):
                            file_path = entry.path
                            if only_modified:
                                if self.is_file_modified(file_path):
                                    if file_path in self.file_metadata:
                                        modified_files.append(file_path)
                                    else:
                                        new_files.append(file_path)
                                    matched.append(file_path)
                            else:
                                matched.append(file_path)
                                
                if entry_count > 0:
                    logging.info(f"Scanned {entry_count} entries in {path}, found {len(matched)} matching files")
                                
            except (PermissionError, OSError) as e:
                logging.warning(f"Permission denied or OS error accessing {path}: {e}")
                return
                
        scan_dir(root_path)
        
        if only_modified:
            logging.info(f"Found {len(new_files)} new files and {len(modified_files)} modified files in {root_path}")
        else:
            logging.info(f"Found {len(matched)} total files in {root_path}")
        
        return matched

    def _remove_existing_db(self):
        """Remove existing database with proper cleanup to avoid lock issues."""
        if os.path.exists(self.persist_directory):
            try:
                # Close any existing vectorstore connections first
                if hasattr(self, 'vectorstore') and self.vectorstore:
                    try:
                        del self.vectorstore
                        self.vectorstore = None
                    except:
                        pass
                
                # Force Python garbage collection to release file handles
                import gc
                gc.collect()
                
                # Give Windows time to release file locks (increased wait time)
                time.sleep(3)
                
                logging.info("Removing existing Chroma DB at %s", self.persist_directory)
                
                # Try to remove the directory
                shutil.rmtree(self.persist_directory)
                logging.info("✅ Successfully removed existing DB")
                
                # Wait again after deletion
                time.sleep(2)
                
            except PermissionError as e:
                # If still locked, it means something else has it open
                # This should NOT happen if the app was properly closed
                logging.error(f"❌ DB is locked - cannot rebuild: {e}")
                logging.error(f"❌ Please close all applications using the database and try again")
                logging.error(f"❌ If the app crashed, restart your computer or manually delete: {self.persist_directory}")
                
                # DO NOT create a new directory - this causes the problem!
                # Instead, raise an exception to stop the rebuild
                raise Exception(f"Database is locked by another process. Please close all apps and try again.")
                    
            except Exception as e:
                logging.error(f"❌ Could not remove existing chroma db: {e}")
                # Raise the exception instead of continuing
                raise
    
    def remove_deleted_files_from_vectorstore(self):
        """Remove files from vectorstore that no longer exist on disk."""
        if not self.vectorstore:
            return
            
        deleted_files = []
        for file_path in list(self.file_metadata.keys()):
            if not os.path.exists(file_path):
                deleted_files.append(file_path)
        
        if deleted_files:
            try:
                # Remove from vectorstore by filtering documents
                for file_path in deleted_files:
                    # Delete documents with matching metadata
                    docs_to_delete = self.vectorstore.get(where={"path": file_path})
                    if docs_to_delete and docs_to_delete.get('ids'):
                        self.vectorstore.delete(ids=docs_to_delete['ids'])
                    
                    # Remove from metadata
                    del self.file_metadata[file_path]
                
                logging.info(f"Removed {len(deleted_files)} deleted files from vectorstore")
                self.save_metadata()
                
            except Exception as e:
                logging.error(f"Error removing deleted files: {e}")

    def update_vectorstore_incremental(self, file_paths):
        """Update vectorstore with only new/modified files."""
        if not file_paths:
            logging.info("No files to update")
            return self.vectorstore
            
        # Create Document objects for new/modified files
        docs = []
        for fp in file_paths:
            doc = Document(page_content=fp, metadata={"path": fp})
            docs.append(doc)
            
            # Update metadata
            file_info = self.get_file_info(fp)
            if file_info:
                self.file_metadata[fp] = file_info

        try:
            if self.vectorstore is None:
                # Create new vectorstore if it doesn't exist
                embeddings = OpenAIEmbeddings()
                self.vectorstore = Chroma(
                    collection_name="paths", 
                    embedding_function=embeddings, 
                    persist_directory=self.persist_directory
                )
            
            # Add new documents
            self.vectorstore.add_documents(docs)
            
            # Save metadata
            self.save_metadata()
            
            logging.info(f"Added {len(file_paths)} files to vectorstore")
            return self.vectorstore
            
        except Exception as e:
            logging.error(f"Error updating vectorstore: {e}")
            return self.vectorstore

    def create_file_vectorstore(self, file_paths, retries=3, delay=1, incremental=False, batch_size=None):
        """Create vectorstore - now redirects to parallel implementation."""
        # Use parallel embedding for better performance
        return self.create_file_vectorstore_with_parallel_embedding(file_paths, retries, incremental)

    def create_file_vectorstore_with_parallel_embedding(self, file_paths, retries=3, incremental=False):
        """Create vectorstore with parallel embedding generation for maximum speed."""
        if incremental:
            return self.update_vectorstore_incremental(file_paths)
            
        total_files = len(file_paths)
        logging.info(f"=" * 60)
        logging.info(f"Creating vectorstore with {total_files} files using parallel embedding")
        
        # Check if GPU is available
        import torch
        import multiprocessing
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # Optimize batch size and workers based on device
        if device == 'cuda':
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            gpu_name = torch.cuda.get_device_name(0)
            logging.info(f"🚀 Using GPU: {gpu_name} ({gpu_memory:.1f} GB)")
            
            if gpu_memory > 8:
                batch_size = 10000
                num_workers = 4
            elif gpu_memory > 4:
                batch_size = 5000
                num_workers = 3
            else:
                batch_size = 2000
                num_workers = 2
        else:
            # CPU: Smaller batches, more workers
            cpu_count = multiprocessing.cpu_count()
            logging.info(f"💻 Using CPU with {cpu_count} cores")
            batch_size = 500
            num_workers = min(cpu_count, 8)  # Max 8 workers
        
        logging.info(f"📊 Batch size: {batch_size}, Workers: {num_workers}")
        logging.info(f"=" * 60)
        
        # Clean up before starting
        self._remove_existing_db()
        
        # Create vectorstore
        vs = Chroma(
            collection_name="paths", 
            embedding_function=self.embeddings, 
            persist_directory=self.persist_directory
        )
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def create_batches(file_list, batch_size):
            """Create batches from file list."""
            return [file_list[i:i + batch_size] for i in range(0, len(file_list), batch_size)]
        
        def process_batch(batch, batch_id):
            """Process a single batch of files."""
            try:
                docs = [Document(page_content=fp, metadata={"path": fp}) for fp in batch]
                
                # Update metadata
                batch_metadata = {}
                for fp in batch:
                    file_info = self.get_file_info(fp)
                    if file_info:
                        batch_metadata[fp] = file_info
                
                return {
                    'success': True,
                    'docs': docs,
                    'metadata': batch_metadata,
                    'batch_id': batch_id,
                    'count': len(batch)
                }
            except Exception as e:
                logging.error(f"❌ Error processing batch {batch_id}: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'batch_id': batch_id
                }
        
        # Create all batches
        all_batches = create_batches(file_paths, batch_size)
        total_batches = len(all_batches)
        
        logging.info(f"Processing {total_batches} batches with {num_workers} parallel workers")
        
        start_time = time.time()
        processed_count = 0
        failed_count = 0
        
        # Use ThreadPoolExecutor for parallel batch processing
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(process_batch, batch, i): i 
                for i, batch in enumerate(all_batches)
            }
            
            # Process results as they complete
            for future in as_completed(future_to_batch):
                batch_id = future_to_batch[future]
                
                try:
                    result = future.result()
                    
                    if result['success']:
                        # Add documents to vectorstore
                        try:
                            vs.add_documents(result['docs'])
                        except Exception as add_error:
                            logging.error(f"❌ Failed to add documents for batch {batch_id}: {add_error}")
                            failed_count += 1
                            continue
                        
                        # Update metadata
                        self.file_metadata.update(result['metadata'])
                        
                        processed_count += result['count']
                        
                        # Save metadata frequently (every 5 batches)
                        if (batch_id + 1) % 5 == 0:
                            try:
                                self.save_metadata()
                            except Exception as save_error:
                                logging.warning(f"⚠️  Failed to save metadata at batch {batch_id}: {save_error}")
                        
                        elapsed = time.time() - start_time
                        rate = processed_count / elapsed if elapsed > 0 else 0
                        progress = (batch_id + 1) / total_batches * 100
                        
                        logging.info(
                            f"📈 Progress: {progress:.1f}% | "
                            f"Batch {batch_id + 1}/{total_batches} | "
                            f"Processed: {processed_count:,}/{total_files:,} files | "
                            f"Speed: {rate:.1f} files/sec"
                        )
                    else:
                        failed_count += 1
                        logging.error(f"❌ Batch {batch_id} failed: {result.get('error')}")
                        
                except Exception as e:
                    failed_count += 1
                    logging.error(f"❌ Error processing batch {batch_id}: {e}")
        
        # Final save with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.save_metadata()
                logging.info("✅ Successfully saved final metadata")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"⚠️  Save attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(2 * (attempt + 1))
                else:
                    logging.error(f"❌ Failed to save metadata after {max_retries} attempts: {e}")
        
        total_time = time.time() - start_time
        avg_speed = processed_count / total_time if total_time > 0 else 0
        
        self.vectorstore = vs
        
        logging.info(f"=" * 60)
        logging.info(f"✅ PARALLEL EMBEDDING COMPLETED!")
        logging.info(f"📊 Total files processed: {processed_count:,}/{total_files:,}")
        logging.info(f"❌ Failed batches: {failed_count}")
        logging.info(f"⏱️  Total time: {total_time:.2f} seconds ({total_time/60:.1f} minutes)")
        logging.info(f"🚀 Average speed: {avg_speed:.1f} files/second")
        if device == 'cuda':
            logging.info(f"⚡ GPU acceleration enabled")
        logging.info(f"=" * 60)
        
        return vs

    def update_vectorstore_incremental(self, file_paths):
        """Update vectorstore with only new/modified files using optimized batching."""
        if not file_paths:
            logging.info("No files to update")
            return self.vectorstore
            
        total_files = len(file_paths)
        batch_size = self.batch_size // 4 if self.use_hf_embeddings else 50  # Smaller batches for incremental
        
        logging.info(f"Incrementally updating {total_files} files in batches of {batch_size}")
        
        # Get or create vectorstore
        if self.vectorstore is None:
            self.vectorstore = Chroma(
                collection_name="paths", 
                embedding_function=self.embeddings, 
                persist_directory=self.persist_directory
            )
        
        # Process in batches
        for i in range(0, total_files, batch_size):
            batch = file_paths[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_files + batch_size - 1) // batch_size
            
            logging.info(f"Processing incremental batch {batch_num}/{total_batches}")
            start_time = time.time()
            
            docs = [Document(page_content=fp, metadata={"path": fp}) for fp in batch]
            
            try:
                self.vectorstore.add_documents(docs)
                
                # Update metadata
                for fp in batch:
                    file_info = self.get_file_info(fp)
                    if file_info:
                        self.file_metadata[fp] = file_info
                
                batch_time = time.time() - start_time
                files_per_sec = len(batch) / batch_time if batch_time > 0 else 0
                logging.info(f"Incremental batch {batch_num} completed in {batch_time:.2f}s ({files_per_sec:.1f} files/sec)")
                
                # Minimal delay
                if batch_num < total_batches:
                    time.sleep(0.1 if self.use_hf_embeddings else 0.5)
                    
            except Exception as e:
                logging.error(f"Failed to process incremental batch {batch_num}: {e}")
        
        self.save_metadata()
        logging.info(f"Incremental update completed for {total_files} files")
        return self.vectorstore

    def run_pipeline(self, root_dirs=None, force_full_rebuild=False):
        """Run the indexing pipeline with smart rebuild detection and parallel processing."""
        # default to all mounted partitions' mountpoints
        if root_dirs is None:
            root_dirs = [p.mountpoint for p in psutil.disk_partitions(all=True)]
        
        # Check what exists
        db_exists = os.path.exists(self.persist_directory)
        metadata_exists = os.path.exists(self.metadata_file)
        has_metadata = bool(self.file_metadata)
        
        logging.info(f"=" * 60)
        logging.info(f"PIPELINE STATUS CHECK")
        logging.info(f"=" * 60)
        logging.info(f"  ⚙️  Force rebuild requested: {force_full_rebuild}")
        logging.info(f"  📁 Database directory exists: {db_exists}")
        logging.info(f"  📄 Metadata file exists: {metadata_exists}")
        logging.info(f"  📊 Metadata records loaded: {len(self.file_metadata):,}")
        logging.info(f"=" * 60)
        
        # Determine if we need full rebuild
        need_full_rebuild = force_full_rebuild
        
        if not need_full_rebuild:
            if not db_exists:
                logging.info("❌ Database directory missing - full rebuild required")
                need_full_rebuild = True
            elif not metadata_exists:
                logging.info("❌ Metadata file missing - full rebuild required")
                need_full_rebuild = True
            elif not has_metadata:
                logging.info("❌ No metadata records - full rebuild required")
                need_full_rebuild = True
            else:
                # Check if vectorstore is actually valid
                try:
                    test_vs = Chroma(
                        collection_name="paths",
                        embedding_function=self.embeddings,
                        persist_directory=self.persist_directory
                    )
                    count = test_vs._collection.count()
                    
                    logging.info(f"📊 Existing vectorstore has {count:,} documents")
                    logging.info(f"📊 Metadata has {len(self.file_metadata):,} file records")
                    
                    # If there's a huge mismatch, consider it corrupted
                    if count == 0 and len(self.file_metadata) > 100:
                        logging.warning("⚠️  Vectorstore is empty but metadata has many files - corruption detected")
                        need_full_rebuild = True
                    elif count < len(self.file_metadata) * 0.5:  # Less than 50% of expected
                        logging.warning(f"⚠️  Vectorstore has only {count:,} documents but metadata shows {len(self.file_metadata):,} files")
                        logging.warning("⚠️  Possible corruption detected - performing full rebuild")
                        need_full_rebuild = True
                    else:
                        logging.info("✅ Vectorstore appears valid - will use existing database")
                        
                        # Set the vectorstore and return it immediately
                        self.vectorstore = test_vs
                        
                        logging.info(f"=" * 60)
                        logging.info(f"✅ USING EXISTING VECTORSTORE")
                        logging.info(f"=" * 60)
                        logging.info(f"  📊 Documents in database: {count:,}")
                        logging.info(f"  📄 Files in metadata: {len(self.file_metadata):,}")
                        logging.info(f"  ✅ No rebuild or scanning needed!")
                        logging.info(f"=" * 60)
                        
                        return test_vs
                        
                except Exception as e:
                    logging.error(f"❌ Failed to verify vectorstore: {e}")
                    need_full_rebuild = True
                    
                    # Clean up failed test instance
                    try:
                        del test_vs
                    except:
                        pass
                    import gc
                    gc.collect()
                    time.sleep(0.5)
        
        start_time = time.time()
        
        if need_full_rebuild:
            logging.info("=" * 60)
            logging.info("🔄 PERFORMING FULL REBUILD")
            logging.info("=" * 60)
            
            # Use parallel scanning for multiple drives
            if len(root_dirs) > 1:
                all_paths = self.find_files_by_extension_parallel(root_dirs)
            else:
                # Single drive, use regular scanning
                all_paths = []
                for root in root_dirs:
                    try:
                        logging.info(f"🔍 Scanning drive: {root}")
                        paths = self.find_files_by_extension(root)
                        logging.info(f"✅ Found {len(paths):,} files in {root}")
                        all_paths.extend(paths)
                    except Exception as e:
                        logging.warning(f"⚠️  Skipping drive {root} due to error: {e}")
            
            scan_time = time.time() - start_time
            logging.info(f"⏱️  Scanning completed in {scan_time:.2f} seconds")
            logging.info(f"📊 Found {len(all_paths):,} matching files total")
            
            if not all_paths:
                logging.warning("⚠️  No files found during scan - this might indicate a configuration issue")
                return None
            
            embedding_start = time.time()
            result = self.create_file_vectorstore(all_paths, incremental=False)
            embedding_time = time.time() - embedding_start
            
            total_time = time.time() - start_time
            logging.info(f"=" * 60)
            logging.info(f"✅ FULL REBUILD COMPLETED")
            logging.info(f"=" * 60)
            logging.info(f"  ⏱️  Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
            logging.info(f"  🔍 Scanning: {scan_time:.2f}s")
            logging.info(f"  🧠 Embedding: {embedding_time:.2f}s")
            logging.info(f"  🚀 Average speed: {len(all_paths) / total_time:.1f} files/second")
            logging.info(f"=" * 60)
            
            return result
        else:
            logging.info("=" * 60)
            logging.info("🔄 PERFORMING INCREMENTAL UPDATE")
            logging.info("=" * 60)
            return self.run_incremental_update(root_dirs)
    
    def run_incremental_update(self, root_dirs=None):
        """Run incremental update with parallel scanning for new/modified files."""
        if root_dirs is None:
            root_dirs = [p.mountpoint for p in psutil.disk_partitions(all=True)]
        
        # Remove deleted files first
        self.remove_deleted_files_from_vectorstore()
        
        start_time = time.time()
        
        # Find only modified files using parallel scanning if multiple drives
        if len(root_dirs) > 1:
            modified_paths = self.find_files_by_extension_parallel(root_dirs, only_modified=True)
        else:
            modified_paths = []
            for root in root_dirs:
                try:
                    logging.info("Scanning for modified files in: %s", root)
                    modified_paths.extend(self.find_files_by_extension(root, only_modified=True))
                except Exception as e:
                    logging.warning("Skipping drive %s due to error: %s", root, e)
        
        scan_time = time.time() - start_time
        
        if modified_paths:
            logging.info("Found %d new/modified files", len(modified_paths))
            embedding_start = time.time()
            result = self.create_file_vectorstore(modified_paths, incremental=True)
            embedding_time = time.time() - embedding_start
            
            total_time = time.time() - start_time
            logging.info(f"Incremental update completed in {total_time:.2f} seconds")
            logging.info(f"  - Scanning: {scan_time:.2f}s")
            logging.info(f"  - Embedding: {embedding_time:.2f}s")
            
            return result
        else:
            logging.info("No new or modified files found")
            return self.get_existing_vectorstore()
    
    def get_existing_vectorstore(self):
        """Get existing vectorstore without rebuilding."""
        if self.vectorstore is None:
            try:
                embeddings = OpenAIEmbeddings()
                self.vectorstore = Chroma(
                    collection_name="paths", 
                    embedding_function=embeddings, 
                    persist_directory=self.persist_directory
                )
            except Exception as e:
                logging.error(f"Failed to load existing vectorstore: {e}")
                return None
        return self.vectorstore
    
    def start_background_updates(self):
        """Start background thread for periodic updates."""
        if self.background_thread and self.background_thread.is_alive():
            logging.info("Background update thread already running")
            return
        
        self.stop_background = False
        self.background_thread = threading.Thread(target=self._background_update_loop, daemon=True)
        self.background_thread.start()
        logging.info(f"Started background updates every {self.update_interval_hours} hours")
    
    def stop_background_updates(self):
        """Stop background update thread."""
        self.stop_background = True
        if self.background_thread and self.background_thread.is_alive():
            self.background_thread.join(timeout=5)
            logging.info("Stopped background update thread")
    
    def _background_update_loop(self):
        """Background thread loop for periodic updates."""
        while not self.stop_background:
            try:
                # Sleep for the update interval
                sleep_time = self.update_interval_hours * 3600  # Convert to seconds
                for _ in range(int(sleep_time)):
                    if self.stop_background:
                        return
                    time.sleep(1)
                
                if not self.stop_background:
                    logging.info("Running scheduled background update")
                    self.run_incremental_update()
                    
            except Exception as e:
                logging.error(f"Error in background update: {e}")
                # Wait a bit before retrying
                time.sleep(300)  # 5 minutes
    
    def force_full_rebuild(self):
        """Force a complete rebuild of the vectorstore."""
        logging.info("Forcing full rebuild of vectorstore")
        return self.run_pipeline(force_full_rebuild=True)
    
    def get_stats(self):
        """Get statistics about the vectorstore."""
        stats = {
            'total_files': len(self.file_metadata),
            'vectorstore_exists': os.path.exists(self.persist_directory),
            'metadata_file_exists': os.path.exists(self.metadata_file),
            'last_update': None
        }
        
        if self.file_metadata:
            last_update_times = [info.get('last_indexed', 0) for info in self.file_metadata.values()]
            if last_update_times:
                stats['last_update'] = datetime.fromtimestamp(max(last_update_times)).isoformat()
        
        return stats

