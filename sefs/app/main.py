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
    update_graph_signal = pyqtSignal(object, object) # files_data, reduced_coords

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
        self.log_signal.emit("Scanning existing files...")
        valid_files = []
        
        # Only scan the root level, not nested folders we created
        for item in os.listdir(self.root_path):
            item_path = os.path.join(self.root_path, item)
            
            # Skip directories (our organized folders)
            if os.path.isdir(item_path):
                continue
            
            # Skip hidden/system files
            if item.startswith('.') or item.endswith('.tmp') or 'sefs.db' in item:
                continue
                
            valid_files.append(os.path.normpath(item_path))
        
        print(f"DEBUG: Found {len(valid_files)} files in root directory")
        
        for file_path in valid_files:
            self.process_file(file_path)
        
        # Clean up DB entries for files that no longer exist
        self._cleanup_missing_files()
        
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
        self.log_signal.emit(f"Event: {event_type} - {os.path.basename(path)}")
        
        # Skip if file is in an organized subfolder (not root level)
        if os.path.dirname(path) != self.root_path:
            return
        
        if event_type == "created":
            self.process_file(path)
            self.recluster_and_update()
        elif event_type == "modified":
            # Check if file content actually changed by comparing hash
            existing = self.db.get_file(path)
            if existing:
                new_hash = self.embedder.compute_file_hash(path)
                if new_hash == existing[2]:  # Hash unchanged
                    print(f"DEBUG: Modification detected but content unchanged for {path}")
                    return
            # Content changed, reprocess
            self.process_file(path)
            self.recluster_and_update()
        elif event_type == "deleted":
            self.db.remove_file(path)
            self.recluster_and_update() # Recluster after deletion
        # For 'moved' events, the file monitor typically reports a 'deleted' event for the old path
        # and a 'created' event for the new path. These are handled by the above logic.

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
        Per-Type Clustering with Content-based AI Naming:
        1. Group files by extension
        2. Cluster each type separately
        3. Use CACHED content samples for AI naming (no file re-reading!)
        4. Move files to Type/AI_Named_Folder structure
        """
        import numpy as np
        
        # 1. Get all files and group by type
        rows = self.db.get_all_files()
        if not rows:
            return

        # Group files by extension
        type_groups = {}  # {extension: [(row, embedding), ...]}
        
        for row in rows:
            # row: id, path, hash, embedding_blob, cluster_id, last_mod, content_sample
            if row[3] and len(row[3]) > 2:  # Has valid embedding
                try:
                    emb = np.frombuffer(row[3], dtype=np.float32)
                    ext = os.path.splitext(row[1])[1].lower()
                    if ext not in type_groups:
                        type_groups[ext] = []
                    type_groups[ext].append((row, emb))
                except Exception as e:
                    print(f"DEBUG: Error loading embedding: {e}")

        if not type_groups:
            print("DEBUG: No files with embeddings found")
            return

        # 2. Cluster each type separately and generate AI names
        all_files_data = []
        all_coords = []
        
        for ext, items in type_groups.items():
            if not items:
                continue
                
            print(f"DEBUG: Processing {len(items)} files of type {ext}")
            rows_for_type = [item[0] for item in items]
            embeddings_for_type = [item[1] for item in items]
            
            # Cluster this type
            labels = self.clusterer.perform_clustering(embeddings_for_type)
            print(f"DEBUG: {ext} clustered into {len(set(labels))} groups")
            
            # Generate AI names for each cluster in this type
            clusters_in_type = set(labels)
            cluster_names = {}  # {cluster_id: "AI_Name"}
            
            for cluster_id in clusters_in_type:
                # Get content samples from DB (NOT by reading files!)
                content_samples = []
                for i, lbl in enumerate(labels):
                    if lbl == cluster_id:
                        row = rows_for_type[i]
                        if row[6]:  # content_sample is at index 6
                            content_samples.append(row[6])
                
                print(f"DEBUG: Generating AI name for {ext} cluster {cluster_id} with {len(content_samples)} samples")
                
                # Generate AI name using cached content
                ai_name = self.ai_namer.generate_folder_name(content_samples[:5], cluster_id)
                cluster_names[cluster_id] = ai_name
                print(f"DEBUG: {ext} Cluster {cluster_id} → '{ai_name}'")
            
            # Process files in this type
            for i, row in enumerate(rows_for_type):
                file_path = os.path.normpath(row[1])
                old_cluster = row[4]
                new_cluster = int(labels[i])
                folder_name = cluster_names.get(new_cluster, f"Semantic_Cluster_{new_cluster}")
                
                # Always move to ensure correct location (even if cluster unchanged)
                if True:  # Always attempt to organize
                    self.log_signal.emit(f"Organizing {os.path.basename(file_path)}")
                    
                    # Update cluster in DB first
                    self.db.update_cluster(file_path, new_cluster)
                    
                    # MOVE FILE with AI name
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
                        self.log_signal.emit(f"→ {folder_name}")
                        
                        # Update for UI
                        row = list(row)
                        row[1] = new_path
                        rows_for_type[i] = tuple(row)
            
            # Reduce dimensions for visualization
            coords = self.clusterer.reduce_dimensions(embeddings_for_type)
            all_coords.extend(coords)
            
            # Prepare UI data
            for i, row in enumerate(rows_for_type):
                display_row = list(row)
                display_row[4] = int(labels[i])
                all_files_data.append(display_row)
        
        # 5. Update UI
        self.update_graph_signal.emit(all_files_data, all_coords)


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
