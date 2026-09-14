"""
Database connection and schema management for DUDE Persistent Memory.
Uses Python's built-in sqlite3.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Iterator


class MemoryDatabase:
    """Manages SQLite connection and table schemas for persistent memory."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default to Project DUDE/data/dude_memory.db
            project_root = Path(__file__).resolve().parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "dude_memory.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """
        Context manager that yields a connection, commits transactions,
        and guarantees connection closing (essential for Windows file locking).
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_schema(self) -> None:
        """Initializes database tables if they do not exist."""
        with self.connect() as conn:
            cursor = conn.cursor()

            # Facts table for user profile, preferences, and long-term facts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact_key TEXT,
                    fact_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Sessions table for conversation tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT DEFAULT 'Untitled Session',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Messages table for turn logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
            """)
