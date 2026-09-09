"""Database layer for coach_bot module."""

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

DB_PATH = "civis.db"  # shared with main app

class CoachDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        """Create coach_bot tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coach_users (
                    user_id INTEGER PRIMARY KEY,
                    status TEXT DEFAULT 'free',
                    trial_start DATE,
                    trial_end DATE,
                    subscription_end DATE,
                    stage TEXT DEFAULT 'welcome',
                    model_preference TEXT DEFAULT 'deepseek',
                    api_key TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coach_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    goal_text TEXT,
                    priority INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES coach_users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coach_checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date DATE,
                    mood INTEGER,
                    progress TEXT,
                    blocked_by TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES coach_users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coach_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES coach_users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coach_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    currency TEXT DEFAULT 'RUB',
                    status TEXT DEFAULT 'pending',
                    payment_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES coach_users(user_id)
                )
            """)

    def get_or_create_user(self, user_id: int) -> Dict[str, Any]:
        """Get user or create with default values."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM coach_users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            
            # Create new user
            conn.execute(
                "INSERT INTO coach_users (user_id, status, stage) VALUES (?, 'free', 'welcome')",
                (user_id,)
            )
            conn.commit()
            cur = conn.execute("SELECT * FROM coach_users WHERE user_id = ?", (user_id,))
            return dict(cur.fetchone())

    def update_user(self, user_id: int, **kwargs):
        """Update user fields."""
        fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [user_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE coach_users SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values
            )
            conn.commit()

    def save_message(self, user_id: int, role: str, content: str):
        """Save a message to history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO coach_messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            conn.commit()

    def get_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent message history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT role, content FROM coach_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cur.fetchall()
            return [dict(row) for row in reversed(rows)]

    def add_goal(self, user_id: int, goal_text: str, priority: int = 1) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO coach_goals (user_id, goal_text, priority) VALUES (?, ?, ?)",
                (user_id, goal_text, priority)
            )
            conn.commit()
            return cur.lastrowid

    def get_active_goals(self, user_id: int) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM coach_goals WHERE user_id = ? AND status = 'active' ORDER BY priority DESC",
                (user_id,)
            )
            return [dict(row) for row in cur.fetchall()]

    def complete_goal(self, goal_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE coach_goals SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (goal_id,)
            )
            conn.commit()

    def add_checkin(self, user_id: int, mood: int, progress: str, blocked_by: str = ""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO coach_checkins (user_id, date, mood, progress, blocked_by) VALUES (?, DATE('now'), ?, ?, ?)",
                (user_id, mood, progress, blocked_by)
            )
            conn.commit()

    def get_checkin_today(self, user_id: int) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM coach_checkins WHERE user_id = ? AND date = DATE('now')",
                (user_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
