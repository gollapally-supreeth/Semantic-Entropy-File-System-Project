import os

class Config:
    APP_NAME = "Semantic Entropy File System"
    VERSION = "2.0.0" # Bumped version for refactor
    DB_PATH = os.path.join("data", "sefs.db")
    # MAX_TEXT_LENGTH removed as we don't read text anymore
    # EMBEDDING_MODEL_NAME removed
    # DBSCAN params removed
    
    EXTENSIONS = ['.txt', '.pdf']
    
    # Mapping for folder names
    FOLDER_MAPPING = {
        '.txt': 'Text_Files',
        '.pdf': 'PDF_Documents'
    }
