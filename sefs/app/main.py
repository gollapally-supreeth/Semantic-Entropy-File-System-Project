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
        self.embedder = EmbeddingEngine()
        self.clusterer = ClusteringEngine()
        self.folder_manager = FolderManager()
        
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
        for root, dirs, files in os.walk(self.root_path):
            # Skip cluster folders to avoid re-scanning organized files if we want strictly
            # But the requirement says "Monitor ROOT". 
            # We should probably process everything in ROOT.
            # However, if we move them, we don't want to re-process endlessly.
            # We rely on DB hashes.
            for file in files:
                if any(file.lower().endswith(ext) for ext in Config.EXTENSIONS):
                    valid_files.append(os.path.join(root, file))
        
        for file_path in valid_files:
            self.process_file(file_path)
        
        self.recluster_and_update()

    def process_event(self, event_type, path):
        self.log_signal.emit(f"Event: {event_type} - {os.path.basename(path)}")
        
        if event_type == 'deleted':
            self.db.remove_file(path)
            self.recluster_and_update()
            return

        # Created, Modified, Moved
        self.process_file(path)
        self.recluster_and_update()

    def process_file(self, file_path):
        # Check if file exists (it might have been deleted quickly)
        if not os.path.exists(file_path):
            return

        # 1. Compute Hash
        file_hash = self.embedder.compute_file_hash(file_path)
        if not file_hash:
            return

        # 2. Check DB
        existing = self.db.get_file(file_path)
        
        if existing and existing[2] == file_hash: # index 2 is file_hash
            # Already processed and hash matches.
            return
        else:
            # Re-compute (basically just register existence now)
            self.log_signal.emit(f"Processing content: {os.path.basename(file_path)}")
            emb = self.embedder.process_file(file_path)
            if emb is not None:
                embedding = emb
                # Save to DB
                # embedding is already bytes, no need for .tobytes() here
                self.db.upsert_file(file_path, file_hash, embedding, datetime.datetime.now())
            else:
                self.log_signal.emit(f"Failed to process {os.path.basename(file_path)}")

    def recluster_and_update(self):
        # 1. Get all files
        rows = self.db.get_all_files()
        if not rows:
            return

        file_paths = []
        file_map = [] # To keep track of which row corresponds to which path

        for row in rows:
            # row: id, path, hash, embedding_blob, cluster_id, last_mod
            file_paths.append(row[1])
            file_map.append(row)

        if not file_paths:
            return

        # 2. Cluster (Now based on extensions)
        labels = self.clusterer.perform_clustering(file_paths)
        
        # 3. Update DB and Move Files
        # We need to see if cluster changed.
        for i, row in enumerate(file_map):
            file_path = row[1]
            old_cluster = row[4]
            new_cluster = int(labels[i])
            
            # Start logic to move file
            # Even if cluster didn't change ID, the folder might not be right if we just started up?
            # But let's stick to "if cluster changed" or "if path is not in correct folder"
            
            # Check if file is in the correct folder
            # We can do this by checking if the cluster ID matches.
            # But since we just computed the cluster ID from the extension, it is "correct" by definition of the engine.
            # We need to check if the file is physically in the right place.
            
            # If we enforce folder structure, we should move it even if DB says it's already in that cluster,
            # unless the path physically matches the target.
            
            # Let's simplify: Always try to move to the target folder. 
            # FolderManager.move_file checks if it's already there.
            
            # Logic:
            # 1. Calculate target folder for new_cluster.
            # 2. Move file.
            # 3. Update DB with new path and new cluster.
            
            # We only strictly need to update DB if something changed.
            
            # Let's try to move everyone to their right place on startup/scan.
            new_path = self.folder_manager.move_file(file_path, new_cluster, self.root_path)
            
            if new_path and new_path != file_path:
                 # It moved
                 self.db.remove_file(file_path)
                 self.db.upsert_file(new_path, row[2], row[3], datetime.datetime.now())
                 self.db.update_cluster(new_path, new_cluster)
                 self.log_signal.emit(f"Moved {os.path.basename(file_path)} -> {os.path.dirname(new_path)}")
                 
                 # Update map for UI
                 new_row = list(row)
                 new_row[1] = new_path
                 new_row[4] = new_cluster
                 file_map[i] = tuple(new_row)
            
            elif new_path == file_path:
                # It was already there, but maybe we need to update cluster ID in DB if it was wrong?
                if old_cluster != new_cluster:
                    self.db.update_cluster(file_path, new_cluster)
                    # Update map for UI
                    new_row = list(row)
                    new_row[4] = new_cluster
                    file_map[i] = tuple(new_row)

        # 4. Reduce Dimensions for UI (Visual grouping)
        # Note: we need to pass the updated paths if we want accuracy, but extensions are same.
        # file_paths list currently has OLD paths.
        # But reduce_dimensions only needs extensions, so OLD paths are fine.
        coords = self.clusterer.reduce_dimensions(file_paths)

        
        # 5. Update UI
        # Refetch everything to be properly synced for UI
        rows = self.db.get_all_files()
        # We need to match rows to coords. 
        # The order of `file_map` was used for `embeddings` which generated `coords`.
        # But we might have modified `rows` (paths changed).
        # We should probably just iterate `file_map` again but update with new paths?
        # Actually, `coords` corresponds to `embeddings` index.
        # `file_map` corresponds to `embeddings` index.
        # So we can zip them.
        
        # Construct display data
        files_data = [] # list of tuples/dicts
        for i, row in enumerate(file_map):
            # row is the OLD row data.
            # If we moved the file, the path in `row` is OLD.
            # We need the current path.
            # We can rely on the fact that we updated the DB.
            # But simpler: just pass the `new_cluster` and `row` (maybe with updated path if we track it).
            
            # Allow the UI to just see the snapshot.
            # If path changed, the UI might show old path until next refresh?
            # Let's try to get fresh data.
            
            # Optimization: Just use file_map but update the cluster_id in it for display
            display_row = list(row)
            display_row[4] = int(labels[i]) # Cluster ID
            files_data.append(display_row)
            
        self.update_graph_signal.emit(files_data, coords)


class SEFSService:
    def __init__(self):
        self.worker = None

    def start_monitoring(self, root_path, main_window):
        if self.worker:
            self.worker.stop()
        
        self.worker = Worker(root_path)
        self.worker.log_signal.connect(main_window.log_panel.add_log)
        self.worker.update_graph_signal.connect(main_window.graph_view.update_graph)
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
