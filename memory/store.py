"""
Jarvis AI Assistant — Memory Store
SQLite-based persistent storage for conversation history and user preferences.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from config import DB_PATH


class MemoryStore:
    """Persistent storage for Jarvis conversations and preferences."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = str(db_path or DB_PATH)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    agent TEXT DEFAULT NULL,
                    metadata TEXT DEFAULT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_message(self, role: str, content: str, agent: str | None = None,
                     metadata: dict | None = None):
        """
        Save a conversation message.

        Args:
            role: "user" or "assistant"
            content: The message text
            agent: Which agent handled it (e.g., "Dev Agent")
            metadata: Optional extra data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO conversations (timestamp, role, content, agent, metadata)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    datetime.now().isoformat(),
                    role,
                    content,
                    agent,
                    json.dumps(metadata) if metadata else None,
                )
            )
            conn.commit()

    def get_recent_messages(self, limit: int = 20) -> list[dict]:
        """
        Get the most recent conversation messages.

        Args:
            limit: Maximum number of messages to return.

        Returns:
            List of message dictionaries.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """SELECT timestamp, role, content, agent
                   FROM conversations
                   ORDER BY id DESC
                   LIMIT ?""",
                (limit,)
            )
            rows = cursor.fetchall()

        messages = []
        for row in reversed(rows):  # Reverse to get chronological order
            messages.append({
                "timestamp": row[0],
                "role": row[1],
                "content": row[2],
                "agent": row[3],
            })

        return messages

    def set_preference(self, key: str, value: str):
        """Save a user preference."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO preferences (key, value, updated_at)
                   VALUES (?, ?, ?)""",
                (key, value, datetime.now().isoformat())
            )
            conn.commit()

    def get_preference(self, key: str, default: str | None = None) -> str | None:
        """Get a user preference."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM preferences WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else default

    def get_conversation_count(self) -> int:
        """Get total number of stored messages."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM conversations")
            return cursor.fetchone()[0]

    def clear_history(self):
        """Clear all conversation history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM conversations")
            conn.commit()
