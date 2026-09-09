"""
Coach Bot Database Layer
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path


class CoachDB:
    """Database operations for coach bot"""
    
    def __init__(self, db_path: str = "civis.db"):
        self.db_path = db_path
        self._init_tables()
    
    def _get_conn(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def _init_tables(self):
        """Create coach bot tables if they don't exist"""
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coach_users (
                    user_id INTEGER PRIMARY KEY,
                    status TEXT DEFAULT 'free',
                    trial_start DATE,
                    trial_end DATE,
                    subscription_end DATE,
                    stage TEXT DEFAULT 'welcome',
                    model_preference TEXT DEFAULT 'deepseek',
                    api_key_encrypted TEXT,
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
                CREATE TABLE IF NOT EXISTS coach_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    payment_id TEXT,
                    amount INTEGER,
                    currency TEXT DEFAULT 'RUB',
                    status TEXT DEFAULT 'pending',
                    plan_type TEXT DEFAULT 'monthly',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES coach_users(user_id)
                )
            """)
            
            conn.commit()
    
    # ============ User operations ============
    
    def get_or_create_user(self, user_id: int) -> Dict[str, Any]:
        """Get user or create if not exists"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT * FROM coach_users WHERE user_id = ?",
                (user_id,)
            )
            row = cur.fetchone()
            
            if row:
                return self._row_to_dict(row, cur.description)
            
            # Create new user
            conn.execute(
                "INSERT INTO coach_users (user_id, status, stage) VALUES (?, ?, ?)",
                (user_id, 'free', 'welcome')
            )
            conn.commit()
            
            return {
                'user_id': user_id,
                'status': 'free',
                'stage': 'welcome',
                'model_preference': 'deepseek',
                'trial_start': None,
                'trial_end': None,
                'subscription_end': None,
            }
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT * FROM coach_users WHERE user_id = ?",
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                return self._row_to_dict(row, cur.description)
            return None
    
    def update_user_stage(self, user_id: int, stage: str):
        """Update user stage"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE coach_users SET stage = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (stage, user_id)
            )
            conn.commit()
    
    def update_user_status(self, user_id: int, status: str):
        """Update user status (free/trial/paid)"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE coach_users SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (status, user_id)
            )
            conn.commit()
    
    def start_trial(self, user_id: int) -> Dict[str, Any]:
        """Start trial period for user"""
        today = date.today()
        trial_end = today + timedelta(days=3)
        
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE coach_users 
                   SET status = 'trial', 
                       trial_start = ?, 
                       trial_end = ?,
                       updated_at = CURRENT_TIMESTAMP 
                   WHERE user_id = ?""",
                (today.isoformat(), trial_end.isoformat(), user_id)
            )
            conn.commit()
        
        return {'trial_start': today.isoformat(), 'trial_end': trial_end.isoformat()}
    
    def activate_subscription(self, user_id: int, months: int = 1):
        """Activate paid subscription"""
        today = date.today()
        end_date = today + timedelta(days=30 * months)
        
        with self._get_conn() as conn:
            conn.execute(
                """UPDATE coach_users 
                   SET status = 'paid', 
                       subscription_end = ?,
                       updated_at = CURRENT_TIMESTAMP 
                   WHERE user_id = ?""",
                (end_date.isoformat(), user_id)
            )
            conn.commit()
    
    def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get user's current status and limits"""
        user = self.get_user(user_id)
        if not user:
            return {'status': 'free', 'can_message': True, 'messages_left': 5}
        
        status = user.get('status', 'free')
        
        # Check trial expiration
        if status == 'trial':
            trial_end = user.get('trial_end')
            if trial_end and date.today() > date.fromisoformat(trial_end):
                self.update_user_status(user_id, 'free')
                status = 'free'
        
        # Check subscription expiration
        if status == 'paid':
            sub_end = user.get('subscription_end')
            if sub_end and date.today() > date.fromisoformat(sub_end):
                self.update_user_status(user_id, 'free')
                status = 'free'
        
        # Count today's messages for free tier
        today = date.today().isoformat()
        with self._get_conn() as conn:
            cur = conn.execute(
                """SELECT COUNT(*) FROM coach_messages 
                   WHERE user_id = ? AND role = 'user' AND DATE(created_at) = ?""",
                (user_id, today)
            )
            count = cur.fetchone()[0]
        
        free_limit = 5
        messages_left = max(0, free_limit - count) if status == 'free' else 999
        
        return {
            'status': status,
            'can_message': status != 'free' or messages_left > 0,
            'messages_left': messages_left,
            'stage': user.get('stage', 'welcome'),
        }
    
    # ============ Message operations ============
    
    def save_message(self, user_id: int, role: str, content: str):
        """Save a message"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO coach_messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            conn.commit()
    
    def get_recent_messages(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent messages for context"""
        with self._get_conn() as conn:
            cur = conn.execute(
                """SELECT role, content, created_at FROM coach_messages 
                   WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
                (user_id, limit)
            )
            rows = cur.fetchall()
            return [
                {'role': row[0], 'content': row[1], 'created_at': row[2]}
                for row in reversed(rows)
            ]
    
    # ============ Goal operations ============
    
    def add_goal(self, user_id: int, goal_text: str, priority: int = 1) -> int:
        """Add a goal"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO coach_goals (user_id, goal_text, priority) VALUES (?, ?, ?)",
                (user_id, goal_text, priority)
            )
            conn.commit()
            return cur.lastrowid
    
    def get_active_goals(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active goals"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT * FROM coach_goals WHERE user_id = ? AND status = 'active' ORDER BY priority DESC",
                (user_id,)
            )
            rows = cur.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'goal_text': row[2],
                    'priority': row[3],
                    'status': row[4],
                    'created_at': row[5],
                    'completed_at': row[6],
                }
                for row in rows
            ]
    
    def complete_goal(self, goal_id: int):
        """Mark goal as completed"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE coach_goals SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                (goal_id,)
            )
            conn.commit()
    
    # ============ Check-in operations ============
    
    def save_checkin(self, user_id: int, mood: int, progress: str, blocked_by: str = ""):
        """Save a daily check-in"""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO coach_checkins (user_id, date, mood, progress, blocked_by) 
                   VALUES (?, DATE('now'), ?, ?, ?)""",
                (user_id, mood, progress, blocked_by)
            )
            conn.commit()
    
    def get_today_checkin(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get today's check-in if exists"""
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT * FROM coach_checkins WHERE user_id = ? AND date = DATE('now')",
                (user_id,)
            )
            row = cur.fetchone()
            if row:
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'date': row[2],
                    'mood': row[3],
                    'progress': row[4],
                    'blocked_by': row[5],
                    'created_at': row[6],
                }
            return None
    
    # ============ Subscription operations ============
    
    def create_subscription(
        self, user_id: int, payment_id: str, amount: int, plan_type: str = 'monthly'
    ) -> int:
        """Create a subscription record"""
        with self._get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO coach_subscriptions (user_id, payment_id, amount, plan_type, status)
                   VALUES (?, ?, ?, ?, 'pending')""",
                (user_id, payment_id, amount, plan_type)
            )
            conn.commit()
            return cur.lastrowid
    
    def confirm_subscription(self, payment_id: str):
        """Confirm a subscription payment"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE coach_subscriptions SET status = 'confirmed', confirmed_at = CURRENT_TIMESTAMP WHERE payment_id = ?",
                (payment_id,)
            )
            conn.commit()
    
    # ============ Helper methods ============
    
    @staticmethod
    def _row_to_dict(row, description):
        """Convert SQLite row to dict"""
        return {col[0]: row[i] for i, col in enumerate(description)}
