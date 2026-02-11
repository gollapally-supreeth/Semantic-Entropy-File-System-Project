import sqlite3
import os
import datetime
from .config import Config

class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DB_PATH
        self._create_tables()

    def _get_connection(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT,
                embedding BLOB,
                cluster_id INTEGER,
                last_modified TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def upsert_file(self, file_path, file_hash, embedding, last_modified):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (file_path, file_hash, embedding, last_modified)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_hash=excluded.file_hash,
                embedding=excluded.embedding,
                last_modified=excluded.last_modified
        ''', (file_path, file_hash, embedding, last_modified))
        conn.commit()
        conn.close()

    def get_file(self, file_path):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM files WHERE file_path = ?', (file_path,))
        row = cursor.fetchone()
        conn.close()
        return row

    def get_all_files(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM files')
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def update_cluster(self, file_path, cluster_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE files SET cluster_id = ? WHERE file_path = ?', (cluster_id, file_path))
        conn.commit()
        conn.close()

    def remove_file(self, file_path):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM files WHERE file_path = ?', (file_path,))
        conn.commit()
        conn.close()

    def clear_all(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM files')
        conn.commit()
        conn.close()
