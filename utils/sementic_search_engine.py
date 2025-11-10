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
    """Get cached HuggingFace embeddings or create new one."""
    global _GLOBAL_HF_EMBEDDINGS_CACHE
    
    if _GLOBAL_HF_EMBEDDINGS_CACHE is not None:
        print("Using cached HuggingFace embeddings model")
        return _GLOBAL_HF_EMBEDDINGS_CACHE
    
    try:
        print("Loading HuggingFace model (this may take a moment on first run)...")
        
        # This model is public and doesn't need authentication
        # Remove any HF_TOKEN from environment to avoid authentication errors
        if "HF_TOKEN" in os.environ:
            del os.environ["HF_TOKEN"]
            print("Removed HF_TOKEN from environment - using public model without authentication")
        else:
            print("Downloading public model without authentication")
        
        # Create cache directory for models
        cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "local_filesearch_agent")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Check if GPU is available
        try:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"Using device for embeddings: {device}")
        except ImportError:
            device = 'cpu'
            print("PyTorch not available, using CPU")
        
        embeddings = HuggingFaceEmbeddings(
            model_name=_GLOBAL_HF_MODEL_NAME,
            cache_folder=cache_dir,
            model_kwargs={'device': device},
            # encode_kwargs={'normalize_embeddings': True}
        )
        
        # Cache the embeddings instance
        _GLOBAL_HF_EMBEDDINGS_CACHE = embeddings
        print(f"Successfully loaded and cached HuggingFace model: {_GLOBAL_HF_MODEL_NAME}")
        print(f"Model cached in: {cache_dir}")
        return embeddings
        
    except Exception as e:
        print(f"Failed to load HuggingFace embeddings: {e}")
        print("Falling back to OpenAI embeddings")
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
        """Remove existing database - only used for full rebuild."""
        if os.path.exists(self.persist_directory):
            try:
                logging.info("Removing existing Chroma DB at %s", self.persist_directory)
                shutil.rmtree(self.persist_directory)
            except Exception as e:
                logging.warning("Could not remove existing chroma db: %s", e)
    
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

    def create_file_vectorstore(self, file_paths, retries=3, delay=1, incremental=False):
        """Create or update vectorstore with file paths using optimized batching."""
        if incremental:
            return self.update_vectorstore_incremental(file_paths)
            
        total_files = len(file_paths)
        logging.info(f"Creating vectorstore with {total_files} files using {'HuggingFace' if self.use_hf_embeddings else 'OpenAI'} embeddings")
        
        # Adjust batch size based on embedding type
        batch_size = self.batch_size if self.use_hf_embeddings else 100
        logging.info(f"Using batch size: {batch_size}")
        
        # Remove existing DB before creating a fresh one
        self._remove_existing_db()
        vs = None
        
        # Process files in batches
        for i in range(0, total_files, batch_size):
            batch = file_paths[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_files + batch_size - 1) // batch_size
            
            logging.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} files)")
            start_time = time.time()
            
            docs = [Document(page_content=fp, metadata={"path": fp}) for fp in batch]
            
            last_exc = None
            for attempt in range(1, retries + 1):
                try:
                    if vs is None:
                        # Create vectorstore on first batch
                        vs = Chroma(
                            collection_name="paths", 
                            embedding_function=self.embeddings, 
                            persist_directory=self.persist_directory
                        )
                    
                    # Add documents for this batch
                    vs.add_documents(docs)
                    
                    # Update metadata for this batch
                    for fp in batch:
                        file_info = self.get_file_info(fp)
                        if file_info:
                            self.file_metadata[fp] = file_info
                    
                    # Save metadata every 10 batches or on last batch
                    if batch_num % 10 == 0 or i + batch_size >= total_files:
                        self.save_metadata()
                        logging.info(f"Saved metadata after batch {batch_num}")
                    
                    batch_time = time.time() - start_time
                    files_per_sec = len(batch) / batch_time if batch_time > 0 else 0
                    logging.info(f"Batch {batch_num} completed in {batch_time:.2f}s ({files_per_sec:.1f} files/sec)")
                    
                    # Minimal delay for HuggingFace, longer for OpenAI
                    if batch_num < total_batches:
                        if self.use_hf_embeddings:
                            time.sleep(0.1)  # 100ms for local embeddings
                        else:
                            time.sleep(1)    # 1s for API embeddings
                    
                    break  # Success, move to next batch
                    
                except Exception as e:
                    last_exc = e
                    logging.warning(f"Batch {batch_num}, attempt {attempt} failed: {e}")
                    if attempt < retries:
                        time.sleep(delay * attempt)  # Exponential backoff
                    else:
                        logging.error(f"Failed to process batch {batch_num} after {retries} attempts")
                        break
        
        if vs:
            self.vectorstore = vs
            total_time = time.time() - start_time if 'start_time' in locals() else 0
            avg_speed = total_files / total_time if total_time > 0 else 0
            logging.info(f"Successfully created vectorstore with {total_files} files")
            logging.info(f"Average processing speed: {avg_speed:.1f} files/second")
            return vs
        else:
            raise RuntimeError("Failed to create vectorstore")

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
        """Run the indexing pipeline with parallel scanning and optimized batching."""
        # default to all mounted partitions' mountpoints
        if root_dirs is None:
            root_dirs = [p.mountpoint for p in psutil.disk_partitions(all=True)]
        
        # Check if we need a full rebuild
        need_full_rebuild = (force_full_rebuild or 
                           not os.path.exists(self.persist_directory) or 
                           not os.path.exists(self.metadata_file) or 
                           not self.file_metadata)
        
        logging.info(f"Pipeline check - Force rebuild: {force_full_rebuild}, DB exists: {os.path.exists(self.persist_directory)}, Metadata exists: {os.path.exists(self.metadata_file)}, Metadata count: {len(self.file_metadata)}")
        
        start_time = time.time()
        
        if need_full_rebuild:
            logging.info("Performing full rebuild of vectorstore with parallel scanning")
            
            # Use parallel scanning for multiple drives
            if len(root_dirs) > 1:
                all_paths = self.find_files_by_extension_parallel(root_dirs)
            else:
                # Single drive, use regular scanning
                all_paths = []
                for root in root_dirs:
                    try:
                        logging.info("Scanning drive: %s", root)
                        paths = self.find_files_by_extension(root)
                        logging.info(f"Found {len(paths)} files in {root}")
                        all_paths.extend(paths)
                    except Exception as e:
                        logging.warning("Skipping drive %s due to error: %s", root, e)
            
            scan_time = time.time() - start_time
            logging.info(f"Scanning completed in {scan_time:.2f} seconds")
            logging.info("Found %d matching files total", len(all_paths))
            
            if not all_paths:
                logging.warning("No files found during scan - this might indicate a configuration issue")
                return None
            
            embedding_start = time.time()
            result = self.create_file_vectorstore(all_paths, incremental=False)
            embedding_time = time.time() - embedding_start
            
            total_time = time.time() - start_time
            logging.info(f"Full pipeline completed in {total_time:.2f} seconds")
            logging.info(f"  - Scanning: {scan_time:.2f}s")
            logging.info(f"  - Embedding: {embedding_time:.2f}s")
            logging.info(f"  - Average speed: {len(all_paths) / total_time:.1f} files/second")
            
            return result
        else:
            logging.info("Performing incremental update")
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

