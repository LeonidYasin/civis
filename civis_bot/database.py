#!/usr/bin/env python3
"""
Database module for Civis bot.
Handles all SQLite operations.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "civis_data.db"

def init_db():
    """Initialize database with all tables"""
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
            status TEXT DEFAULT 'registered',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if 'language' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
        logger.info("Added 'language' column to users table")
    
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
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

def get_user(tg_id):
    """Get user data by tg_id"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        columns = ['tg_id', 'username', 'name', 'telegram_contact', 'about_text', 'user_values', 'role', 'format', 'language', 'status', 'created_at', 'updated_at']
        return dict(zip(columns, row))
    return None

def save_user(tg_id, username, **kwargs):
    """Save or update user"""
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

def get_session(tg_id):
    """Get session state for user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT state, data FROM sessions WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row[0], json.loads(row[1]) if row[1] else {}
    return None, {}

def set_session(tg_id, state, data=None):
    """Set session state for user"""
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
    """Clear session for user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM sessions WHERE tg_id = ?", (tg_id,))
    conn.commit()
    conn.close()

# --- OFFERS AND REQUESTS ---
def save_offer(tg_id, text):
    """Save an offer"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO offers (tg_id, text, created_at) VALUES (?, ?, ?)",
                 (tg_id, text, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_request(tg_id, text):
    """Save a request"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO requests (tg_id, text, created_at) VALUES (?, ?, ?)",
                 (tg_id, text, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_citizens():
    """Get all users with completed profiles"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username, name, role, user_values FROM users WHERE status = 'completed'")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_my_offers(tg_id):
    """Get offers by user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, text, created_at FROM offers WHERE tg_id = ? ORDER BY created_at DESC", (tg_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_my_requests(tg_id):
    """Get requests by user"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, text, created_at FROM requests WHERE tg_id = ? ORDER BY created_at DESC", (tg_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_offers():
    """Get all offers"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tg_id, text, created_at FROM offers ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_requests():
    """Get all requests"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tg_id, text, created_at FROM requests ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return rows
