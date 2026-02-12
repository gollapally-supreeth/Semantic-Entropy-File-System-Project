import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class Config:
    APP_NAME = "Semantic Entropy File System"
    VERSION = "4.0.0" # Semantic Restoration
    DB_PATH = os.path.join("data", "sefs.db")
    
    # Semantic params
    MAX_TEXT_LENGTH = 10000
    EMBEDDING_MODEL_NAME = 'all-mpnet-base-v2'  # Upgraded from MiniLM for better accuracy
    DBSCAN_EPS = 0.3  # Reduced for better semantic separation (was 0.5)
    DBSCAN_MIN_SAMPLES = 2  # Increased to 2 for more stable clusters
    
    # AI Naming Configuration
    USE_AI_NAMING = True  # Enabled for semantic naming
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')  # Set via environment variable
    GEMINI_MODEL = 'gemini-2.5-flash'  # Upgraded to 1.5 Flash for better accuracy and speed
    
    # We restrict to text-readable files for semantic analysis
    EXTENSIONS = ['.txt', '.pdf', '.md', '.log', '.csv', '.docx', '.doc']
