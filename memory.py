"""
memory.py - Dual-Tier SQLite Persistent Memory System
"""
import sqlite3
import time
from config import DB_PATH

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Long-term facts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS long_term (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL
            )
        """)
        # Short-term context log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS short_term (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp REAL
            )
        """)
        # Expiry memory
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temp_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note TEXT,
                expires_at REAL
            )
        """)
        conn.commit()

def set_fact(key: str, value: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO long_term (key, value, updated_at) VALUES (?, ?, ?)",
            (key, value, time.time())
        )
        conn.commit()

def get_fact(key: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM long_term WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else ""

def log_conversation(role: str, content: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO short_term (role, content, timestamp) VALUES (?, ?, ?)",
            (role, content, time.time())
        )
        conn.commit()

def get_recent_context(limit: int = 6) -> list:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM short_term ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        return list(reversed(rows))
