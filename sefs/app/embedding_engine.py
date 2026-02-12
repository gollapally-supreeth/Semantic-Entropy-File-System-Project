from sentence_transformers import SentenceTransformer
import os
import hashlib
import fitz  # PyMuPDF
from .config import Config

class EmbeddingEngine:
    def __init__(self):
        # Initialize the model.
        print("Loading Embedding Model...")
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL_NAME)
        print("Model Loaded.")

    def compute_file_hash(self, file_path):
        """Computes SHA256 hash of the file content."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"Error hashing file {file_path}: {e}")
            return None

    def extract_text(self, file_path):
        """Extracts text from PDF, TXT, or DOCX files."""
        text = ""
        try:
            ext = os.path.splitext(file_path)[1].lower()
            # Basic text reading
            if ext in ['.txt', '.md', '.log', '.csv', '.py', '.js', '.html']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read(Config.MAX_TEXT_LENGTH)
            elif ext == '.pdf':
                doc = fitz.open(file_path)
                for page in doc:
                    text += page.get_text()
                    if len(text) > Config.MAX_TEXT_LENGTH:
                        break
                text = text[:Config.MAX_TEXT_LENGTH]
                doc.close()
            elif ext in ['.docx', '.doc']:
                # Extract from Word documents
                try:
                    import docx
                    doc = docx.Document(file_path)
                    for para in doc.paragraphs:
                        text += para.text + "\n"
                        if len(text) > Config.MAX_TEXT_LENGTH:
                            break
                    text = text[:Config.MAX_TEXT_LENGTH]
                except ImportError:
                    print("python-docx not installed, skipping .docx file")
                except Exception as e:
                    print(f"Error reading .docx file: {e}")
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
        return text

    def generate_embedding(self, text):
        """Generates semantic embedding using neural sentence transformer."""
        if not text or len(text.strip()) == 0:
            return None
        
        try:
            # Clean and preprocess text for better embeddings
            cleaned_text = self._preprocess_text(text)
            
            # Generate embedding using neural network
            embedding = self.model.encode(cleaned_text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def _preprocess_text(self, text):
        """Clean and preprocess text for better semantic embeddings"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Remove special characters but keep punctuation for context
        import re
        text = re.sub(r'[^\w\s\.\,\!\?\-]', ' ', text)
        
        # Limit length while keeping complete sentences
        if len(text) > Config.MAX_TEXT_LENGTH:
            text = text[:Config.MAX_TEXT_LENGTH]
            # Try to end at sentence boundary
            last_period = text.rfind('.')
            if last_period > Config.MAX_TEXT_LENGTH * 0.8:
                text = text[:last_period + 1]
        
        return text.strip()

    def process_file(self, file_path):
        """Orchestrates reading and embedding generation."""
        text = self.extract_text(file_path)
        if text and len(text.strip()) > 0:
            return self.generate_embedding(text)
        return None
