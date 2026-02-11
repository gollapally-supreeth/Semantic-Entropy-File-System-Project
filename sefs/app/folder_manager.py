import os
import shutil
import time

class FolderManager:
    """
    Handles the physical organization of files on the disk.
    """

    def create_cluster_folders(self, root_path, cluster_ids):
        """
        Ensures folders for all cluster IDs exist.
        Cluster -1 is usually 'noise' in DBSCAN, we can map it to 'Unclassified'.
        """
        for cid in cluster_ids:
            folder_name = self._get_folder_name(cid)
            folder_path = os.path.join(root_path, folder_name)
            if not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path)
                except OSError as e:
                    print(f"Error creating folder {folder_path}: {e}")

    def move_file(self, file_path, cluster_id, root_path):
        """
        Moves the file to the appropriate cluster folder.
        """
        if not os.path.exists(file_path):
            return None # File might have been deleted

        folder_name = self._get_folder_name(cluster_id)
        target_folder = os.path.join(root_path, folder_name)
        
        # Ensure target folder exists (redundancy check)
        if not os.path.exists(target_folder):
            try:
                os.makedirs(target_folder)
            except OSError:
                pass

        filename = os.path.basename(file_path)
        destination_path = os.path.join(target_folder, filename)

        # Don't move if it's already there
        if os.path.abspath(file_path) == os.path.abspath(destination_path):
            return destination_path

        # Handle name collision
        if os.path.exists(destination_path):
            base, ext = os.path.splitext(filename)
            timestamp = int(time.time())
            new_filename = f"{base}_{timestamp}{ext}"
            destination_path = os.path.join(target_folder, new_filename)

        try:
            shutil.move(file_path, destination_path)
            return destination_path
        except Exception as e:
            print(f"Error moving file {file_path} to {destination_path}: {e}")
            return None

    def _get_folder_name(self, cluster_id):
        # We need to map cluster_id back to extension.
        # This is a bit roundabout because main.py passes an int ID.
        # But wait, clustering_engine returns IDs based on sorted(Config.EXTENSIONS).
        # So we can map back.
        
        from .config import Config
        exts = sorted(Config.EXTENSIONS)
        if 0 <= cluster_id < len(exts):
            ext = exts[cluster_id]
            return Config.FOLDER_MAPPING.get(ext, "Unclassified")
        return "Unclassified"
