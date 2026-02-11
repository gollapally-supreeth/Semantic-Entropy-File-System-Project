import os

class Config:
    APP_NAME = "Semantic Entropy File System"
    VERSION = "4.0.0" # Semantic Restoration
    DB_PATH = os.path.join("data", "sefs.db")
    
    # Semantic params
    MAX_TEXT_LENGTH = 10000
    EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
    DBSCAN_EPS = 0.3  # Reduced for better semantic separation (was 0.5)
    DBSCAN_MIN_SAMPLES = 2  # Increased to 2 for more stable clusters
    
    # AI Naming Configuration
    USE_AI_NAMING = True  # Set to False to use generic names
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')  # Set via environment variable
    GEMINI_MODEL = 'gemini-1.5-flash'
    
    # We restrict to text-readable files for semantic analysis
    EXTENSIONS = ['.txt', '.pdf', '.md', '.log', '.csv', '.docx', '.doc']
