import os
import shutil
import time

class FolderManager:
    """
    Handles the physical organization of files on the disk.
    Now supports dynamic folder generation based on extension.
    """

    
    def _get_type_folder_name(self, extension):
        # Maps extension to a high-level Type Folder
        if not extension:
            return "Misc_Files"
            
        ext = extension.lower()
        if ext == '.pdf':
            return "PDF_Documents"
        elif ext == '.txt':
            return "Text_Files"
        elif ext in ['.doc', '.docx']:
            return "Word_Documents"
        elif ext in ['.md', '.log']:
            return "Documentation"
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            return "Image_Files"
        elif ext in ['.mp3', '.wav', '.flac']:
             return "Audio_Files"
        elif ext in ['.mp4', '.mkv', '.avi', '.mov']:
             return "Video_Files"
        elif ext in ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.json', '.xml']:
             return "Source_Code"
        elif ext in ['.zip', '.rar', '.7z', '.tar', '.gz']:
             return "Archives"
        else:
             # Fallback: Just use the extension name
             return f"{ext.lstrip('.').upper()}_Files"

    def _get_cluster_folder_name(self, cluster_id):
        # Semantic ID based naming
        if cluster_id == -1:
            return "Unclassified_Noise"
        return f"Semantic_Cluster_{cluster_id}"

    def move_file(self, file_path, folder_name, root_path):
        """
        Moves file to: Root / Cluster_Folder / Type_Folder / File
        NEW STRUCTURE: Semantic clusters first, then file types within each cluster
        """
        # Normalize all paths
        file_path = os.path.normpath(file_path)
        root_path = os.path.normpath(root_path)
        
        if not os.path.exists(file_path):
            print(f"WARNING: Cannot move {file_path} - file not found")
            return None 

        ext = os.path.splitext(file_path)[1].lower()
        
        # 1. Use provided cluster/semantic folder name (e.g., "Finance", "AI_Research")
        cluster_folder = folder_name
        
        # 2. Determine Type Folder within the cluster
        type_folder = self._get_type_folder_name(ext)
        
        # Full Target Directory: Root / Cluster / Type
        target_dir = os.path.join(root_path, cluster_folder, type_folder)
        
        # Ensure target folder exists
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
            except OSError:
                pass

        filename = os.path.basename(file_path)
        destination_path = os.path.join(target_dir, filename)
        
        # Check if already there
        if os.path.abspath(file_path) == os.path.abspath(destination_path):
            return file_path

        # Handle name collision - replace existing file
        if os.path.exists(destination_path):
            try:
                os.remove(destination_path)
                print(f"DEBUG: Replaced existing file at {destination_path}")
            except Exception as e:
                print(f"Warning: Could not remove old file: {e}")
                base, ext = os.path.splitext(filename)
                timestamp = int(time.time())
                new_filename = f"{base}_{timestamp}{ext}"
                destination_path = os.path.join(target_dir, new_filename)

        try:
            shutil.move(file_path, destination_path)
            return destination_path
        except Exception as e:
            print(f"Error moving file {file_path}: {e}")
            return None

    # We remove create_cluster_folders as it's dynamic now.
