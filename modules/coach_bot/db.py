"""
Database operations for Coach Bot
"""

import sqlite3
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any
import json

from .config import config


class CoachDB:
    """Database handler for Coach Bot"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database_url.replace('sqlite:///', '')
        self._init_tables()
    
    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def _init_tables(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
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
            
            # Goals table
            cursor.execute("""
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
            
            # Check-ins table
            cursor.execute("""
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
            
            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coach_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES coach_users(user_id)
                )
            """)
            
            # Payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coach_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount INTEGER,
                    currency TEXT DEFAULT 'RUB',
                    plan TEXT,
                    payment_id TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES coach_users(user_id)
                )
            """)
            
            conn.commit()
    
    # --- User operations ---
    
    def get_or_create_user(self, user_id: int) -> Dict[str, Any]:
        """Get user or create if not exists"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM coach_users WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row, cursor)
            else:
                cursor.execute(
                    "INSERT INTO coach_users (user_id) VALUES (?)",
                    (user_id,)
                )
                conn.commit()
                cursor.execute(
                    "SELECT * FROM coach_users WHERE user_id = ?",
                    (user_id,)
                )
                return self._row_to_dict(cursor.fetchone(), cursor)
    
    def update_user(self, user_id: int, **kwargs):
        """Update user fields"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            fields = []
            values = []
            for key, value in kwargs.items():
                if key in ['status', 'stage', 'model_preference', 'api_key']:
                    fields.append(f"{key} = ?")
                    values.append(value)
                elif key in ['trial_start', 'trial_end', 'subscription_end']:
                    fields.append(f"{key} = ?")
                    values.append(value)
            
            if fields:
                fields.append("updated_at = CURRENT_TIMESTAMP")
                values.append(user_id)
                query = f"UPDATE coach_users SET {', '.join(fields)} WHERE user_id = ?"
                cursor.execute(query, values)
                conn.commit()
    
    def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get user status and limits"""
        user = self.get_or_create_user(user_id)
        today = date.today()
        
        # Check subscription status
        is_trial_active = False
        is_subscribed = False
        
        if user.get('trial_end'):
            trial_end = datetime.strptime(user['trial_end'], '%Y-%m-%d').date()
            is_trial_active = today <= trial_end
        
        if user.get('subscription_end'):
            sub_end = datetime.strptime(user['subscription_end'], '%Y-%m-%d').date()
            is_subscribed = today <= sub_end
        
        # Count today's messages
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM coach_messages WHERE user_id = ? AND DATE(created_at) = DATE('now')",
                (user_id,)
            )
            today_messages = cursor.fetchone()[0]
        
        return {
            'status': user.get('status', 'free'),
            'stage': user.get('stage', 'welcome'),
            'is_trial_active': is_trial_active,
            'is_subscribed': is_subscribed,
            'today_messages': today_messages,
            'free_limit': config.free_messages_per_day,
            'model_preference': user.get('model_preference', 'deepseek'),
            'has_api_key': bool(user.get('api_key')),
        }
    
    # --- Messages ---
    
    def save_message(self, user_id: int, role: str, content: str):
        """Save a message"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO coach_messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            conn.commit()
    
    def get_recent_messages(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for context"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM coach_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            return [{'role': row[0], 'content': row[1]} for row in reversed(rows)]
    
    # --- Goals ---
    
    def add_goal(self, user_id: int, goal_text: str, priority: int = 1) -> int:
        """Add a goal"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO coach_goals (user_id, goal_text, priority) VALUES (?, ?, ?)",
                (user_id, goal_text, priority)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_active_goals(self, user_id: int) -> List[Dict[str, Any]]:
        """Get active goals"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, goal_text, priority, status FROM coach_goals WHERE user_id = ? AND status = 'active' ORDER BY priority DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [{'id': r[0], 'text': r[1], 'priority': r[2], 'status': r[3]} for r in rows]
    
    def complete_goal(self, goal_id: int):
        """Mark goal as completed"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE coach_goals SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (goal_id,)
            )
            conn.commit()
    
    # --- Check-ins ---
    
    def save_checkin(self, user_id: int, mood: int = None, progress: str = None, blocked_by: str = None):
        """Save a daily check-in"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO coach_checkins (user_id, date, mood, progress, blocked_by) 
                   VALUES (?, DATE('now'), ?, ?, ?)""",
                (user_id, mood, progress, blocked_by)
            )
            conn.commit()
    
    def get_today_checkin(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get today's check-in if exists"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT mood, progress, blocked_by FROM coach_checkins WHERE user_id = ? AND date = DATE('now')",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {'mood': row[0], 'progress': row[1], 'blocked_by': row[2]}
            return None
    
    # --- Payments ---
    
    def create_payment(self, user_id: int, amount: int, plan: str, payment_id: str) -> int:
        """Create a payment record"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO coach_payments (user_id, amount, plan, payment_id) VALUES (?, ?, ?, ?)",
                (user_id, amount, plan, payment_id)
            )
            conn.commit()
            return cursor.lastrowid
    
    def confirm_payment(self, payment_id: str):
        """Confirm a payment and activate subscription"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE coach_payments SET status = 'completed' WHERE payment_id = ?",
                (payment_id,)
            )
            
            # Get user_id from payment
            cursor.execute(
                "SELECT user_id, plan FROM coach_payments WHERE payment_id = ?",
                (payment_id,)
            )
            row = cursor.fetchone()
            if row:
                user_id, plan = row
                end_date = date.today() + timedelta(days=30)
                cursor.execute(
                    "UPDATE coach_users SET status = 'paid', subscription_end = ? WHERE user_id = ?",
                    (end_date.isoformat(), user_id)
                )
            conn.commit()
    
    # --- Helper ---
    
    def _row_to_dict(self, row, cursor) -> Dict[str, Any]:
        """Convert SQLite row to dict"""
        if not row:
            return {}
        columns = [description[0] for description in cursor.description]
        return {columns[i]: row[i] for i in range(len(columns))}
