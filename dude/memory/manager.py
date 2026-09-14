"""
Memory Manager for DUDE.
Provides high-level APIs for managing persistent facts and session histories.
"""

import uuid
from typing import List, Dict, Any, Optional
from dude.memory.database import MemoryDatabase


class MemoryManager:
    """
    Coordinates long-term fact storage and session conversation persistence in SQLite.
    """

    def __init__(self, db: Optional[MemoryDatabase] = None):
        self.db = db or MemoryDatabase()
        self.current_session_id: str = ""
        self.start_new_session("Active Session")

    def start_new_session(self, title: str = "Chat Session") -> str:
        """Initializes a new session ID and saves it to the sessions table."""
        self.current_session_id = uuid.uuid4().hex[:12]
        try:
            with self.db.connect() as conn:
                conn.execute(
                    "INSERT INTO sessions (id, title) VALUES (?, ?)",
                    (self.current_session_id, title)
                )
                conn.commit()
        except Exception:
            # Non-blocking fail-safe: session ID still set in memory
            pass
        return self.current_session_id

    # ---------------------------------------------------------
    # Fact & User Profile Management
    # ---------------------------------------------------------

    def add_fact(self, fact_value: str, fact_key: Optional[str] = None) -> int:
        """
        Stores a persistent fact about the user or system.
        Returns the inserted fact row ID.
        """
        clean_val = fact_value.strip()
        if not clean_val:
            raise ValueError("Fact value cannot be empty.")

        clean_key = fact_key.strip() if fact_key else None

        with self.db.connect() as conn:
            cursor = conn.cursor()
            # Avoid duplicate identical facts
            cursor.execute(
                "SELECT id FROM facts WHERE fact_value = ?",
                (clean_val,)
            )
            existing = cursor.fetchone()
            if existing:
                return existing["id"]

            cursor.execute(
                "INSERT INTO facts (fact_key, fact_value) VALUES (?, ?)",
                (clean_key, clean_val)
            )
            conn.commit()
            return cursor.lastrowid or 0

    def get_facts(self) -> List[Dict[str, Any]]:
        """Returns all persistent facts currently stored."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, fact_key, fact_value, created_at FROM facts ORDER BY id ASC"
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def delete_fact(self, fact_id: int) -> bool:
        """Deletes a fact by its ID. Returns True if a record was removed."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_facts(self) -> int:
        """Erases all stored facts. Returns the count of deleted facts."""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM facts")
            conn.commit()
            return cursor.rowcount

    def format_facts_for_prompt(self) -> str:
        """
        Formats all persistent facts into a clean block suitable for injecting
        into DUDE's system prompt.
        """
        facts = self.get_facts()
        if not facts:
            return ""

        lines = [
            "--- RECALLED USER FACTS & PERSISTENT MEMORY ---",
            "The following are verified persistent facts about the user and past context. "
            "Use them seamlessly in conversation whenever relevant:"
        ]
        for f in facts:
            if f.get("fact_key"):
                lines.append(f"- [{f['fact_key']}]: {f['fact_value']}")
            else:
                lines.append(f"- {f['fact_value']}")
        lines.append("-----------------------------------------------")
        return "\n".join(lines)

    def auto_extract_facts(self, text: str) -> List[int]:
        """
        Scans natural conversation input for personal facts (name, favorites, location, notes)
        and automatically stores them into persistent memory if found.
        Returns a list of newly stored fact IDs.
        """
        import re
        t = text.strip()
        new_ids = []

        # 1. Name detection
        m = re.search(
            r'\b(?:my name (?:is|\x27s)|call me)\s+([A-Za-z0-9_-]+)(?:\s+(?!and\b|or\b|but\b|who\b)([A-Za-z0-9_-]+))?\b',
            t,
            re.IGNORECASE
        )
        if m:
            name = f"{m.group(1)} {m.group(2)}" if m.group(2) else m.group(1)
            new_ids.append(self.add_fact(f"Name is {name.strip()}", fact_key="name"))

        # 2. Favorite detection
        m = re.search(
            r'\bmy fav(?:orite)?\s+([a-zA-Z\s]{2,20})\s+(?:is|are)\s+([A-Za-z0-9_-]+)(?:\s+(?!and\b|or\b|but\b)([A-Za-z0-9_-]+))?\b',
            t,
            re.IGNORECASE
        )
        if m:
            item = m.group(1).strip()
            val = f"{m.group(2)} {m.group(3)}" if m.group(3) else m.group(2)
            new_ids.append(self.add_fact(f"Favorite {item} is {val.strip()}", fact_key="preference"))

        # 3. Location detection
        m = re.search(
            r'\bi (?:live in|am from|come from)\s+([A-Za-z\s,]{2,30})\b',
            t,
            re.IGNORECASE
        )
        if m:
            place = m.group(1).strip()
            if not re.search(r'\b(and|or|but)\b', place, re.IGNORECASE):
                new_ids.append(self.add_fact(f"Lives in {place}", fact_key="location"))

        # 4. Explicit 'remember that ...' (excluding questions)
        m = re.search(r'\bremember\s+(?:that\s+|:\s*)?([^.!?\n]{3,80})', t, re.IGNORECASE)
        if m:
            note = m.group(1).strip()
            if not t.endswith("?") and not t.lower().startswith(("do you remember", "can you remember")):
                new_ids.append(self.add_fact(note, fact_key="note"))

        return new_ids

    # ---------------------------------------------------------
    # Message Persistence
    # ---------------------------------------------------------

    def record_message(self, role: str, content: str) -> None:
        """Persists a single message turn into the SQLite messages table."""
        if not self.current_session_id:
            self.start_new_session()

        try:
            with self.db.connect() as conn:
                conn.execute(
                    "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                    (self.current_session_id, role, content)
                )
                conn.execute(
                    "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (self.current_session_id,)
                )
                conn.commit()
        except Exception:
            # Non-blocking fail-safe
            pass

    def get_session_messages(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, str]]:
        """Retrieves stored message turns for a given session."""
        target_session = session_id or self.current_session_id
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ?",
                    (target_session, limit)
                )
                return [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]
        except Exception:
            return []

    def get_recent_sessions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Returns recent conversation sessions and message counts."""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT s.id, s.title, s.created_at, s.updated_at, COUNT(m.id) as message_count
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    GROUP BY s.id
                    ORDER BY s.updated_at DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []
