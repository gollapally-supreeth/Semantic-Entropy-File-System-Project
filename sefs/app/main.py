import sys
import os
import queue
import time
import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication

from .config import Config
from .database import DatabaseManager
from .embedding_engine import EmbeddingEngine
from .clustering_engine import ClusteringEngine
from .folder_manager import FolderManager
from .file_monitor import FileMonitor
from .ui.main_window import MainWindow
from .ai_namer import AINamer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Worker(QThread):
    log_signal = pyqtSignal(str)
    update_graph_signal = pyqtSignal(object, object, object) # files_data, reduced_coords, cluster_names

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path
        self._is_running = True
        self.event_queue = queue.Queue()
        
        # Initialize Backend Components
        self.db = DatabaseManager()
        
        # Clear database on startup for fresh state
        print("Clearing database for fresh start...")
        self.db.clear_all()
        
        self.embedder = EmbeddingEngine()
        self.clusterer = ClusteringEngine()
        self.folder_manager = FolderManager()
        self.ai_namer = AINamer()  # Initialize AI naming service
        
        # Monitor
        self.monitor = FileMonitor(self.root_path, self.handle_file_event)

    def handle_file_event(self, event_type, path):
        self.event_queue.put((event_type, path))

    def run(self):
        self.log_signal.emit("Initializing engines...")
        self.monitor.start()
        self.log_signal.emit(f"Monitoring started on {self.root_path}")
        
        # Initial scan
        self.scan_existing_files()

        while self._is_running:
            try:
                # Process events with a timeout to allow checking _is_running
                event = self.event_queue.get(timeout=1.0)
                event_type, path = event
                self.process_event(event_type, path)
                self.event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.log_signal.emit(f"Error in worker loop: {e}")

    def stop(self):
        self._is_running = False
        self.monitor.stop()
        self.wait()

    def scan_existing_files(self):
        self.log_signal.emit("Scanning directory...")
        valid_files = []
        
        # Recursive scan to find all supported files
        for root, dirs, files in os.walk(self.root_path):
            # Skip the .gemini or other hidden folders often ignored
            if '.gemini' in root or '.git' in root:
                continue
                
            for file in files:
                # Skip hidden/system files
                if file.startswith('.') or file.endswith('.tmp') or 'sefs.db' in file:
                    continue
                
                # Check extension
                ext = os.path.splitext(file)[1].lower()
                if ext in Config.EXTENSIONS:
                    file_path = os.path.normpath(os.path.join(root, file))
                    valid_files.append(file_path)
        
        print(f"DEBUG: Found {len(valid_files)} total files in directory")
        
        for file_path in valid_files:
            self.process_file(file_path)
        
        # Clean up DB entries for files that no longer exist
        self._cleanup_missing_files()
        
        # First clustering
        self.recluster_and_update()
    
    def _cleanup_missing_files(self):
        """Remove DB entries for files that no longer exist"""
        rows = self.db.get_all_files()
        removed = 0
        for row in rows:
            file_path = os.path.normpath(row[1])
            if not os.path.exists(file_path):
                self.db.remove_file(file_path)
                removed += 1
        if removed > 0:
            print(f"DEBUG: Cleaned up {removed} missing file entries from DB")

    def process_event(self, event_type, path):
        path = os.path.normpath(path)
        
        # Check if file extension is supported
        ext = os.path.splitext(path)[1].lower()
        if ext not in Config.EXTENSIONS:
            return
        
        # For 'created' or 'moved', check if this is an AI organization move
        # We can detect this by seeing if the file is already in a sub-subfolder (Cluster/Type/File)
        # and its content hash is already in the database with that path.
        if event_type in ["created", "moved"]:
            existing = self.db.get_file(path)
            if existing:
                # File already exists at this path in DB, likely moved there by us
                # or just a redundant OS event. Skip to prevent loop.
                return

        self.log_signal.emit(f"Event: {event_type} - {os.path.basename(path)}")
        
        if event_type in ["created", "moved"]:
            # Add small delay to ensure file write is complete
            time.sleep(0.5)
            if os.path.exists(path):
                self.process_file(path)
                self.recluster_and_update()
        elif event_type == "modified":
            # Check if file content actually changed
            existing = self.db.get_file(path)
            if existing:
                new_hash = self.embedder.compute_file_hash(path)
                if new_hash == existing[2]:
                    return
            
            if os.path.exists(path):
                self.process_file(path)
                self.recluster_and_update()
        elif event_type == "deleted":
            # Just remove from DB, don't recluster immediately to avoid noise
            self.db.remove_file(path)

    def process_file(self, file_path):
        # Normalize path
        file_path = os.path.normpath(file_path)
        print(f"DEBUG: Processing {file_path}")
        
        if not os.path.exists(file_path):
            print(f"DEBUG: File not found {file_path}")
            return

        # 1. Compute Hash
        file_hash = self.embedder.compute_file_hash(file_path)
        if not file_hash:
            print(f"DEBUG: Hash failed for {file_path}")
            return

        # 2. Check DB
        existing = self.db.get_file(file_path)
        
        if existing and existing[2] == file_hash:
            print(f"DEBUG: File already processed (hash match) {file_path}")
            return
        
        # 3. Extract text and generate embedding
        self.log_signal.emit(f"Processing: {os.path.basename(file_path)}")
        print(f"DEBUG: Generating embedding for {file_path}")
        
        text_content = self.embedder.extract_text(file_path)
        
        if text_content and len(text_content.strip()) > 10:
            # Generate embedding
            emb = self.embedder.generate_embedding(text_content)
            
            if emb is not None:
                # Store first 500 chars as content sample for AI naming
                content_sample = text_content[:500]
                
                # Save to DB with content sample
                self.db.upsert_file(
                    file_path, 
                    file_hash, 
                    emb.tobytes(), 
                    datetime.datetime.now(),
                    content_sample
                )
                print(f"DEBUG: Saved embedding + content sample for {file_path}")
            else:
                self.log_signal.emit(f"Failed to process {os.path.basename(file_path)}")
                print(f"DEBUG: Embedding generation failed for {file_path}")
        else:
            print(f"DEBUG: No text content extracted from {file_path}")

    def recluster_and_update(self):
        """
        SEMANTIC CLUSTERING - Cluster ALL files together by content!
        1. Get all files regardless of extension
        2. Cluster ALL together using HDBSCAN + UMAP
        3. Generate AI names for semantic clusters
        4. Move files to Cluster/Type structure
        """
        import numpy as np
        
        # 1. Get all files and group by type
        rows = self.db.get_all_files()
        if not rows:
            return

        # Collect ALL files with embeddings
        all_files = []
        all_embeddings = []
        
        for row in rows:
            # row: id, path, hash, embedding_blob, cluster_id, last_mod, content_sample
            if row[3] and len(row[3]) > 2:  # Has valid embedding
                try:
                    emb = np.frombuffer(row[3], dtype=np.float32)
                    all_files.append(row)
                    all_embeddings.append(emb)
                except Exception as e:
                    print(f"DEBUG: Error loading embedding: {e}")

        if not all_files:
            print("DEBUG: No files with embeddings found")
            return
        
        print(f"DEBUG: Clustering {len(all_files)} files SEMANTICALLY (all types together)")

        # 2. Cluster ALL files together by semantic content
        labels = self.clusterer.perform_clustering(all_embeddings)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"DEBUG: Found {n_clusters} semantic clusters across all file types")
        
        # 3. Generate AI names for each semantic cluster
        clusters = set(labels)
        cluster_names = {}  # {cluster_id: "AI_Name"}
        
        for cluster_id in clusters:
            # Get content samples from this cluster
            content_samples = []
            for i, lbl in enumerate(labels):
                if lbl == cluster_id:
                    row = all_files[i]
                    if row[6]:  # content_sample
                        content_samples.append(row[6])
            
            print(f"DEBUG: Generating AI name for cluster {cluster_id} with {len(content_samples)} files")
            
            # Generate AI name
            ai_name = self.ai_namer.generate_folder_name(content_samples[:5], cluster_id)
            cluster_names[cluster_id] = ai_name
            print(f"DEBUG: Cluster {cluster_id} → '{ai_name}'")
        
        # 4. Move files to Cluster/Type structure
        all_files_data = []
        
        for i, row in enumerate(all_files):
            file_path = os.path.normpath(row[1])
            new_cluster = int(labels[i])
            folder_name = cluster_names.get(new_cluster, f"Semantic_Cluster_{new_cluster}")
            
            # Update cluster in DB
            self.db.update_cluster(file_path, new_cluster)
            
            # Move file to Cluster/Type/file structure
            new_path = self.folder_manager.move_file(file_path, folder_name, self.root_path)
            
            if new_path and new_path != file_path:
                # File was moved - update DB path
                self.db.remove_file(file_path)
                self.db.upsert_file(
                    new_path,
                    row[2],  # hash
                    row[3],  # embedding
                    datetime.datetime.now(),
                    row[6]   # content_sample
                )
                self.db.update_cluster(new_path, new_cluster)
                self.log_signal.emit(f"→ {folder_name}/{os.path.basename(new_path)}")
                
                # Update row for UI
                row = list(row)
                row[1] = new_path
                row[4] = new_cluster
                all_files[i] = tuple(row)
            
            # Prepare UI data
            display_row = list(all_files[i])
            display_row[4] = new_cluster
            all_files_data.append(display_row)
        
        # 5. Visualization
        all_coords = self.clusterer.reduce_dimensions(all_embeddings)
        
        # 5. Update UI
        self.update_graph_signal.emit(all_files_data, all_coords, cluster_names)


class SEFSService:
    def __init__(self):
        self.worker = None

    def start_monitoring(self, root_path, main_window):
        if self.worker:
            self.worker.stop()
        
        self.worker = Worker(root_path)
        self.worker.log_signal.connect(main_window.log_panel.add_log)
        self.worker.update_graph_signal.connect(main_window.update_graph_display)
        self.worker.start()

    def stop_monitoring(self):
        if self.worker:
            self.worker.stop()
            self.worker = None

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    service = SEFSService()

    def on_start(path):
        service.start_monitoring(path, window)

    def on_stop():
        service.stop_monitoring()

    window.start_monitoring_signal.connect(on_start)
    window.stop_monitoring_signal.connect(on_stop)
    
    window.show()
    sys.exit(app.exec())
