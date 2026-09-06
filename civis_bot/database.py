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
    
    # Offers table with category and extended fields
    cur.execute("""
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            category TEXT DEFAULT 'general',
            text TEXT,
            price INTEGER,
            property_type TEXT,
            property_area INTEGER,
            property_address TEXT,
            property_rooms INTEGER,
            created_at TEXT
        )
    """)
    
    # Check for missing columns in offers
    cur.execute("PRAGMA table_info(offers)")
    offer_columns = [col[1] for col in cur.fetchall()]
    if 'category' not in offer_columns:
        cur.execute("ALTER TABLE offers ADD COLUMN category TEXT DEFAULT 'general'")
        logger.info("Added 'category' column to offers table")
    if 'price' not in offer_columns:
        cur.execute("ALTER TABLE offers ADD COLUMN price INTEGER")
        logger.info("Added 'price' column to offers table")
    if 'property_type' not in offer_columns:
        cur.execute("ALTER TABLE offers ADD COLUMN property_type TEXT")
        logger.info("Added 'property_type' column to offers table")
    if 'property_area' not in offer_columns:
        cur.execute("ALTER TABLE offers ADD COLUMN property_area INTEGER")
        logger.info("Added 'property_area' column to offers table")
    if 'property_address' not in offer_columns:
        cur.execute("ALTER TABLE offers ADD COLUMN property_address TEXT")
        logger.info("Added 'property_address' column to offers table")
    if 'property_rooms' not in offer_columns:
        cur.execute("ALTER TABLE offers ADD COLUMN property_rooms INTEGER")
        logger.info("Added 'property_rooms' column to offers table")
    
    # Requests table with category and extended fields
    cur.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            category TEXT DEFAULT 'general',
            text TEXT,
            price_min INTEGER,
            price_max INTEGER,
            property_type TEXT,
            property_area_min INTEGER,
            property_area_max INTEGER,
            property_address TEXT,
            property_rooms_min INTEGER,
            property_rooms_max INTEGER,
            created_at TEXT
        )
    """)
    
    # Check for missing columns in requests
    cur.execute("PRAGMA table_info(requests)")
    req_columns = [col[1] for col in cur.fetchall()]
    if 'category' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN category TEXT DEFAULT 'general'")
        logger.info("Added 'category' column to requests table")
    if 'price_min' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN price_min INTEGER")
        logger.info("Added 'price_min' column to requests table")
    if 'price_max' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN price_max INTEGER")
        logger.info("Added 'price_max' column to requests table")
    if 'property_type' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN property_type TEXT")
        logger.info("Added 'property_type' column to requests table")
    if 'property_area_min' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN property_area_min INTEGER")
        logger.info("Added 'property_area_min' column to requests table")
    if 'property_area_max' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN property_area_max INTEGER")
        logger.info("Added 'property_area_max' column to requests table")
    if 'property_address' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN property_address TEXT")
        logger.info("Added 'property_address' column to requests table")
    if 'property_rooms_min' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN property_rooms_min INTEGER")
        logger.info("Added 'property_rooms_min' column to requests table")
    if 'property_rooms_max' not in req_columns:
        cur.execute("ALTER TABLE requests ADD COLUMN property_rooms_max INTEGER")
        logger.info("Added 'property_rooms_max' column to requests table")
    
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
    
    # Embeddings cache table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            tg_id INTEGER PRIMARY KEY,
            embedding TEXT,
            provider TEXT,
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
def save_offer(tg_id, text, category='general', **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Build insert query dynamically
    fields = ['tg_id', 'category', 'text', 'created_at']
    values = [tg_id, category, text, datetime.now().isoformat()]
    
    # Add optional fields
    optional_fields = ['price', 'property_type', 'property_area', 'property_address', 'property_rooms']
    for field in optional_fields:
        if field in kwargs and kwargs[field] is not None:
            fields.append(field)
            values.append(kwargs[field])
    
    placeholders = ', '.join(['?'] * len(values))
    cur.execute(f"INSERT INTO offers ({', '.join(fields)}) VALUES ({placeholders})", values)
    
    conn.commit()
    conn.close()

def get_all_offers(category=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if category:
        cur.execute("""
            SELECT id, tg_id, category, text, price, property_type, property_area, property_address, property_rooms, created_at
            FROM offers WHERE category = ? ORDER BY created_at DESC
        """, (category,))
    else:
        cur.execute("""
            SELECT id, tg_id, category, text, price, property_type, property_area, property_address, property_rooms, created_at
            FROM offers ORDER BY created_at DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_my_offers(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, category, text, price, property_type, property_area, property_address, property_rooms, created_at
        FROM offers WHERE tg_id = ? ORDER BY created_at DESC
    """, (tg_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_offer(offer_id, tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM offers WHERE id = ? AND tg_id = ?", (offer_id, tg_id))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0

# --- REQUEST FUNCTIONS ---
def save_request(tg_id, text, category='general', **kwargs):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Build insert query dynamically
    fields = ['tg_id', 'category', 'text', 'created_at']
    values = [tg_id, category, text, datetime.now().isoformat()]
    
    # Add optional fields
    optional_fields = ['price_min', 'price_max', 'property_type', 'property_area_min', 
                      'property_area_max', 'property_address', 'property_rooms_min', 'property_rooms_max']
    for field in optional_fields:
        if field in kwargs and kwargs[field] is not None:
            fields.append(field)
            values.append(kwargs[field])
    
    placeholders = ', '.join(['?'] * len(values))
    cur.execute(f"INSERT INTO requests ({', '.join(fields)}) VALUES ({placeholders})", values)
    
    conn.commit()
    conn.close()

def get_all_requests(category=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    if category:
        cur.execute("""
            SELECT id, tg_id, category, text, price_min, price_max, property_type,
                   property_area_min, property_area_max, property_address,
                   property_rooms_min, property_rooms_max, created_at
            FROM requests WHERE category = ? ORDER BY created_at DESC
        """, (category,))
    else:
        cur.execute("""
            SELECT id, tg_id, category, text, price_min, price_max, property_type,
                   property_area_min, property_area_max, property_address,
                   property_rooms_min, property_rooms_max, created_at
            FROM requests ORDER BY created_at DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_my_requests(tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, category, text, price_min, price_max, property_type,
               property_area_min, property_area_max, property_address,
               property_rooms_min, property_rooms_max, created_at
        FROM requests WHERE tg_id = ? ORDER BY created_at DESC
    """, (tg_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def delete_request(req_id, tg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM requests WHERE id = ? AND tg_id = ?", (req_id, tg_id))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def find_matching_offers_for_request(req_tg_id, limit=10):
    """Find offers that match a request using AI embeddings"""
    # Get the request
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, category, text, price_min, price_max, property_type,
               property_area_min, property_area_max, property_address,
               property_rooms_min, property_rooms_max
        FROM requests WHERE tg_id = ? AND category = 'real_estate'
    """, (req_tg_id,))
    req = cur.fetchone()
    conn.close()
    
    if not req:
        return []
    
    # Get all real estate offers
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tg_id, text, price, property_type, property_area, property_address, property_rooms
        FROM offers WHERE category = 'real_estate'
    """)
    offers = cur.fetchall()
    conn.close()
    
    if not offers:
        return []
    
    # Simple rule-based matching (will be enhanced with AI later)
    matches = []
    req_price_min = req[3] or 0
    req_price_max = req[4] or float('inf')
    req_type = req[5]
    req_area_min = req[6] or 0
    req_area_max = req[7] or float('inf')
    req_rooms_min = req[9] or 0
    req_rooms_max = req[10] or float('inf')
    
    for offer in offers:
        offer_id, tg_id, text, price, prop_type, area, address, rooms = offer
        
        # Check price range
        if price and (price < req_price_min or price > req_price_max):
            continue
        
        # Check property type
        if req_type and prop_type and req_type.lower() != prop_type.lower():
            continue
        
        # Check area range
        if area and (area < req_area_min or area > req_area_max):
            continue
        
        # Check rooms range
        if rooms and (rooms < req_rooms_min or rooms > req_rooms_max):
            continue
        
        matches.append({
            'offer_id': offer_id,
            'tg_id': tg_id,
            'text': text,
            'price': price,
            'property_type': prop_type,
            'area': area,
            'address': address,
            'rooms': rooms
        })
    
    return matches[:limit]

def find_matching_requests_for_offer(offer_tg_id, limit=10):
    """Find requests that match an offer using AI embeddings"""
    # Get the offer
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, category, text, price, property_type, property_area, property_address, property_rooms
        FROM offers WHERE tg_id = ? AND category = 'real_estate'
    """, (offer_tg_id,))
    offer = cur.fetchone()
    conn.close()
    
    if not offer:
        return []
    
    # Get all real estate requests
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tg_id, text, price_min, price_max, property_type,
               property_area_min, property_area_max, property_address,
               property_rooms_min, property_rooms_max
        FROM requests WHERE category = 'real_estate'
    """)
    requests = cur.fetchall()
    conn.close()
    
    if not requests:
        return []
    
    # Simple rule-based matching
    matches = []
    offer_price = offer[3]
    offer_type = offer[4]
    offer_area = offer[5]
    offer_rooms = offer[7]
    
    for req in requests:
        req_id, tg_id, text, price_min, price_max, req_type, area_min, area_max, address, rooms_min, rooms_max = req
        
        # Check price range
        if offer_price:
            if price_min and offer_price < price_min:
                continue
            if price_max and offer_price > price_max:
                continue
        
        # Check property type
        if req_type and offer_type and req_type.lower() != offer_type.lower():
            continue
        
        # Check area range
        if offer_area:
            if area_min and offer_area < area_min:
                continue
            if area_max and offer_area > area_max:
                continue
        
        # Check rooms range
        if offer_rooms:
            if rooms_min and offer_rooms < rooms_min:
                continue
            if rooms_max and offer_rooms > rooms_max:
                continue
        
        matches.append({
            'request_id': req_id,
            'tg_id': tg_id,
            'text': text,
            'price_min': price_min,
            'price_max': price_max,
            'property_type': req_type,
            'area_min': area_min,
            'area_max': area_max,
            'rooms_min': rooms_min,
            'rooms_max': rooms_max
        })
    
    return matches[:limit]

# --- CITIZEN FUNCTIONS ---
def get_all_citizens():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT username, name, role, user_values FROM users WHERE status = 'completed'")
    rows = cur.fetchall()
    conn.close()
    return rows

def search_citizens(query):
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
    
    if sub['plan'] == 'premium':
        return True
    
    return sub['matches_used'] < sub['matches_limit']

def get_matches_remaining(tg_id):
    sub = get_subscription(tg_id)
    if not sub:
        create_subscription(tg_id)
        sub = get_subscription(tg_id)
    
    if sub['plan'] == 'premium':
        return float('inf')
    
    return max(0, sub['matches_limit'] - sub['matches_used'])
