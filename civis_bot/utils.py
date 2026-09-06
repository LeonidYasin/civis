#!/usr/bin/env python3
"""
Utility functions for Civis bot.
"""

import json
import logging
import requests
from datetime import datetime
import sqlite3
from pathlib import Path

from database import get_user
from locales import TEXTS, get_value_buttons, get_roles, get_formats

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "civis_data.db"

def get_text(tg_id, key, **kwargs):
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    text = TEXTS.get(lang, TEXTS['en']).get(key, TEXTS['en'][key])
    return text.format(**kwargs) if kwargs else text

# Re-export from locales
def get_value_buttons(lang):
    return get_value_buttons(lang)

def get_roles(lang):
    return get_roles(lang)

def get_formats(lang):
    return get_formats(lang)

def get_embedding_profile(tg_id):
    user = get_user(tg_id)
    if not user:
        return None
    
    profile = {
        'name': user.get('name', ''),
        'role': user.get('role', ''),
        'values': user.get('user_values', ''),
        'format': user.get('format', ''),
        'about': user.get('about_text', ''),
        'embedding_version': '1.0'
    }
    return json.dumps(profile, indent=2)

def get_profile_text(user):
    """Convert user dict to text for embedding"""
    return f"""Name: {user.get('name', '')}
Role: {user.get('role', '')}
Values: {user.get('user_values', '')}
About: {user.get('about_text', '')}"""

def get_embedding(text, openai_key):
    """Generate embedding for text using OpenAI"""
    try:
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "text-embedding-3-small",
            "input": text
        }
        
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Embedding API error: {response.text}")
            return None
        
        data = response.json()
        return data.get('data', [{}])[0].get('embedding')
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def get_cached_embedding(tg_id, openai_key):
    """Get cached embedding or generate new one"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if embedding exists and is fresh (less than 7 days old)
    cur.execute(
        "SELECT embedding, updated_at FROM embeddings WHERE tg_id = ?",
        (tg_id,)
    )
    row = cur.fetchone()
    
    if row:
        embedding_json, updated_at = row
        # If less than 7 days old, use cached
        if updated_at:
            try:
                updated = datetime.fromisoformat(updated_at)
                if (datetime.now() - updated).days < 7:
                    conn.close()
                    return json.loads(embedding_json)
            except:
                pass
    
    conn.close()
    
    # Generate new embedding
    user = get_user(tg_id)
    if not user:
        return None
    
    text = get_profile_text(user)
    embedding = get_embedding(text, openai_key)
    
    if embedding:
        # Save to cache
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                tg_id INTEGER PRIMARY KEY,
                embedding TEXT,
                updated_at TEXT
            )
        """)
        cur.execute("""
            INSERT OR REPLACE INTO embeddings (tg_id, embedding, updated_at)
            VALUES (?, ?, ?)
        """, (tg_id, json.dumps(embedding), datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    return embedding

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors"""
    if not a or not b or len(a) != len(b):
        return 0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    
    if norm_a == 0 or norm_b == 0:
        return 0
    
    return dot_product / (norm_a * norm_b)

def find_matches(tg_id, openai_key, limit=5):
    """Find matching citizens using embeddings"""
    # Get current user's embedding
    my_embedding = get_cached_embedding(tg_id, openai_key)
    if not my_embedding:
        return None
    
    # Get all citizens
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT tg_id, username, name, role, user_values, about_text
        FROM users
        WHERE status = 'completed' AND tg_id != ?
    """, (tg_id,))
    citizens = cur.fetchall()
    conn.close()
    
    if not citizens:
        return []
    
    matches = []
    
    for citizen_tg_id, username, name, role, values, about in citizens:
        # Get or generate embedding for citizen
        citizen_embedding = get_cached_embedding(citizen_tg_id, openai_key)
        if not citizen_embedding:
            continue
        
        score = cosine_similarity(my_embedding, citizen_embedding)
        score_percent = int(score * 100)
        
        # Only show matches above 20% (lower threshold for more results)
        if score_percent >= 20:
            matches.append({
                'tg_id': citizen_tg_id,
                'username': username or 'unknown',
                'name': name or 'Unknown',
                'role': role or 'N/A',
                'values': values or 'N/A',
                'about': about or '',
                'score': score_percent
            })
    
    # Sort by score descending and limit
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches[:limit]

def generate_match_explanation(user, match):
    """Generate human-readable explanation for a match"""
    parts = []
    
    # Role match
    if user.get('role') and match.get('role'):
        if user['role'].lower() == match['role'].lower():
            parts.append(f"Same role: {match['role']}")
        else:
            parts.append(f"Role: {user['role']} ↔ {match['role']}")
    
    # Values match
    user_values = set(user.get('user_values', '').split(', ')) if user.get('user_values') else set()
    match_values = set(match.get('values', '').split(', ')) if match.get('values') else set()
    common_values = user_values & match_values
    if common_values:
        parts.append(f"Shared values: {', '.join(list(common_values)[:3])}")
    
    # Format match
    if user.get('format') and match.get('format'):
        if user['format'] == match['format']:
            parts.append(f"Same format: {match['format']}")
    
    if not parts:
        parts.append("Good semantic match based on profile similarity")
    
    return " • ".join(parts)
