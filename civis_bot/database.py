#!/usr/bin/env python3
"""
Database module for Civis bot.
Handles all SQLite operations for users, sessions, offers, requests, and subscriptions.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "civis_data.db"

def init_db():
    """Initialize all database tables"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            username TEXT,
            name TEXT,
            telegram_contact TEXT,
            about_text TEXT,
            user_values TEXT,
            role TEXT,
            format TEXT,
            language TEXT DEFAULT 'en',
            openai_key TEXT,
            status TEXT DEFAULT 'registered',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # Add openai_key column if missing
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if 'openai_key' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN openai_key TEXT")
        logger.info("Added 'openai_key' column to users table")
    
    # Sessions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            tg_id INTEGER PRIMARY KEY,
            state TEXT,
            data TEXT,
            updated_at TEXT
        )
    """)
    
    # Offers table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            text TEXT,
            created_at TEXT
        )
    """)
    
    # Requests table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            text TEXT,
            created_at TEXT
        )
    """)
    
    # Subscriptions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            tg_id INTEGER PRIMARY KEY,
            plan TEXT DEFAULT 'free',
            valid_until TEXT,
            matches_used INTEGER DEFAULT 0,
            matches_limit INTEGER DEFAULT 3,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# --- USER FUNCTIONS ---
def get_user(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        columns = ['tg_id', 'username', 'name', 'telegram_contact', 'about_text', 'user_values', 'role', 'format', 'language', 'openai_key', 'status', 'created_at', 'updated_at']
        return dict(zip(columns, row))
    return None

def save_user(tg_id, username, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,))
    exists = cur.fetchone()
    
    if exists:
        fields = []
        values = []
        for key, val in kwargs.items():
            if key != 'tg_id':
                fields.append(f"{key} = ?")
                values.append(val)
        values.append(datetime.now().isoformat())
        values.append(tg_id)
        cur.execute(f"UPDATE users SET {', '.join(fields)}, updated_at = ? WHERE tg_id = ?", values)
    else:
        fields = ['tg_id', 'username', 'created_at', 'updated_at']
        values = [tg_id, username, datetime.now().isoformat(), datetime.now().isoformat()]
        for key, val in kwargs.items():
            if key not in ['tg_id', 'username']:
                fields.append(key)
                values.append(val)
        placeholders = ', '.join(['?'] * len(values))
        cur.execute(f"INSERT INTO users ({', '.join(fields)}) VALUES ({placeholders})", values)
    
    conn.commit()
    conn.close()

def save_openai_key(tg_id, key):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET openai_key = ?, updated_at = ? WHERE tg_id = ?",
                 (key, datetime.now().isoformat(), tg_id))
    conn.commit()
    conn.close()

def get_openai_key(tg_id):
    user = get_user(tg_id)
    return user.get('openai_key') if user else None

# --- SESSION FUNCTIONS ---
def get_session(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT state, data FROM sessions WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0], json.loads(row[1]) if row[1] else {}
    return None, {}

def set_session(tg_id, state, data=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    data_json = json.dumps(data or {})
    cur.execute("""
        INSERT OR REPLACE INTO sessions (tg_id, state, data, updated_at)
        VALUES (?, ?, ?, ?)
    """, (tg_id, state, data_json, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def clear_session(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

# --- OFFER FUNCTIONS ---
def save_offer(tg_id, text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO offers (tg_id, text, created_at) VALUES (?, ?, ?)",
                 (tg_id, text, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_offers():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, tg_id, text, created_at FROM offers ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_my_offers(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, text, created_at FROM offers WHERE tg_id = ? ORDER BY created_at DESC", (tg_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_offer(offer_id, tg_id):
    """Delete an offer by ID if it belongs to the user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM offers WHERE id = ? AND tg_id = ?", (offer_id, tg_id))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# --- REQUEST FUNCTIONS ---
def save_request(tg_id, text):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO requests (tg_id, text, created_at) VALUES (?, ?, ?)",
                 (tg_id, text, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_requests():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, tg_id, text, created_at FROM requests ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_my_requests(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, text, created_at FROM requests WHERE tg_id = ? ORDER BY created_at DESC", (tg_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_request(req_id, tg_id):
    """Delete a request by ID if it belongs to the user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM requests WHERE id = ? AND tg_id = ?", (req_id, tg_id))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# --- CITIZEN FUNCTIONS ---
def get_all_citizens():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username, name, role, user_values FROM users WHERE status = 'completed'")
    rows = cur.fetchall()
    conn.close()
    return rows

def search_citizens(query):
    """Search citizens by name, role, or values"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    search_pattern = f"%{query}%"
    cur.execute("""
        SELECT username, name, role, user_values, about_text
        FROM users
        WHERE status = 'completed'
        AND (name LIKE ? OR role LIKE ? OR user_values LIKE ? OR about_text LIKE ?)
        LIMIT 20
    """, (search_pattern, search_pattern, search_pattern, search_pattern))
    rows = cur.fetchall()
    conn.close()
    return rows

# --- SUBSCRIPTION FUNCTIONS ---
def get_subscription(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM subscriptions WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        columns = ['tg_id', 'plan', 'valid_until', 'matches_used', 'matches_limit', 'created_at', 'updated_at']
        return dict(zip(columns, row))
    return None

def create_subscription(tg_id, plan='free', matches_limit=3):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO subscriptions (tg_id, plan, valid_until, matches_used, matches_limit, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tg_id, plan, None, 0, matches_limit, datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()

def update_subscription_plan(tg_id, plan, matches_limit=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if matches_limit is None:
        matches_limit = 999 if plan == 'premium' else 3 if plan == 'free' else 3
    cur.execute("""
        UPDATE subscriptions SET plan = ?, matches_limit = ?, updated_at = ?
        WHERE tg_id = ?
    """, (plan, matches_limit, datetime.now().isoformat(), tg_id))
    conn.commit()
    conn.close()

def increment_matches_used(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE subscriptions SET matches_used = matches_used + 1, updated_at = ? WHERE tg_id = ?",
                 (datetime.now().isoformat(), tg_id))
    conn.commit()
    conn.close()

def can_use_match(tg_id):
    sub = get_subscription(tg_id)
    if not sub:
        create_subscription(tg_id)
        sub = get_subscription(tg_id)
    
    # Check if premium or has matches left
    if sub['plan'] == 'premium':
        return True
    
    # Free plan: check limit
    return sub['matches_used'] < sub['matches_limit']

def get_matches_remaining(tg_id):
    sub = get_subscription(tg_id)
    if not sub:
        create_subscription(tg_id)
        sub = get_subscription(tg_id)
    
    if sub['plan'] == 'premium':
        return float('inf')
    
    return max(0, sub['matches_limit'] - sub['matches_used'])
