import os
import hashlib

class EmbeddingEngine:
    """
    Refactored to only handle file hashing.
    Name kept as EmbeddingEngine to minimize immediate refactoring validation, 
    but logic is purely hashing now.
    """
    def __init__(self):
        pass

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

    def process_file(self, file_path):
        """
        Formerly generated embeddings. Now just returns a dummy value 
        to indicate successful processing (since we only care about hash/existence).
        """
        # We don't need text extraction or embedding anymore.
        # Just return a non-None value to signal "processed".
        # We return a dummy bytes object to satisfy DB BLOB constraint if we keep schema.
        return b'\x00' 
