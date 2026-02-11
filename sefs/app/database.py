import sqlite3
import os
import datetime
from .config import Config

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self._migrate_schema()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT,
                embedding BLOB,
                cluster_id INTEGER DEFAULT -1,
                last_modified TIMESTAMP,
                content_sample TEXT
            )
        ''')
        self.conn.commit()
    
    def _migrate_schema(self):
        """Add content_sample column if it doesn't exist"""
        try:
            self.cursor.execute("PRAGMA table_info(files)")
            columns = [row[1] for row in self.cursor.fetchall()]
            if 'content_sample' not in columns:
                print("DB Migration: adding content_sample column...")
                self.cursor.execute("ALTER TABLE files ADD COLUMN content_sample TEXT")
                self.conn.commit()
                print("Migration complete.")
        except Exception as e:
            print(f"Migration error (can be ignored): {e}")

    def upsert_file(self, file_path, file_hash, embedding, last_modified, content_sample=None):
        """Insert or update file record"""
        file_path = os.path.normpath(file_path)
        
        self.cursor.execute('''
            INSERT INTO files (file_path, file_hash, embedding, last_modified, content_sample)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash=excluded.file_hash,
                embedding=excluded.embedding,
                last_modified=excluded.last_modified,
                content_sample=excluded.content_sample
        ''', (file_path, file_hash, embedding, last_modified, content_sample))
        self.conn.commit()

    def get_file(self, file_path):
        file_path = os.path.normpath(file_path)
        self.cursor.execute('SELECT * FROM files WHERE file_path = ?', (file_path,))
        return self.cursor.fetchone()

    def get_all_files(self):
        self.cursor.execute('SELECT * FROM files')
        return self.cursor.fetchall()
    
    def update_cluster(self, file_path, cluster_id):
        file_path = os.path.normpath(file_path)
        self.cursor.execute('UPDATE files SET cluster_id = ? WHERE file_path = ?', (cluster_id, file_path))
        self.conn.commit()

    def remove_file(self, file_path):
        file_path = os.path.normpath(file_path)
        self.cursor.execute('DELETE FROM files WHERE file_path = ?', (file_path,))
        self.conn.commit()

    def clear_all(self):
        self.cursor.execute('DELETE FROM files')
        self.conn.commit()

    def close(self):
        self.conn.close()
