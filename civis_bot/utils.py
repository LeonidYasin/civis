#!/usr/bin/env python3
"""
Utility functions for Civis bot.
"""

import json
import logging
import requests
from datetime import datetime

from database import get_user
from locales import TEXTS, VALUE_MAP, get_value_buttons as _get_value_buttons, get_roles as _get_roles, get_formats as _get_formats

logger = logging.getLogger(__name__)

def get_text(tg_id, key, **kwargs):
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    text = TEXTS.get(lang, TEXTS['en']).get(key, TEXTS['en'][key])
    return text.format(**kwargs) if kwargs else text

def get_value_buttons(lang):
    return _get_value_buttons(lang)

def get_roles(lang):
    return _get_roles(lang)

def get_formats(lang):
    return _get_formats(lang)

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

def get_embedding(user, openai_key):
    """Generate embedding for a user profile using OpenAI"""
    try:
        # Build text representation
        text = f"""Name: {user.get('name', '')}
Role: {user.get('role', '')}
Values: {user.get('user_values', '')}
About: {user.get('about_text', '')}"""
        
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

def find_matches(my_embedding, citizens, openai_key):
    """Find matching citizens using embeddings"""
    matches = []
    
    for username, name, role, values in citizens:
        # Skip if it's the same user (username will be different)
        # Build text for citizen
        text = f"Name: {name}\nRole: {role}\nValues: {values}"
        
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
                continue
            
            data = response.json()
            embedding = data.get('data', [{}])[0].get('embedding')
            
            if embedding:
                score = cosine_similarity(my_embedding, embedding)
                score_percent = int(score * 100)
                
                if score_percent > 30:  # Only show matches above 30%
                    matches.append({
                        'username': username,
                        'name': name,
                        'role': role,
                        'user_values': values,
                        'score': score_percent
                    })
        except Exception as e:
            logger.error(f"Error matching with {username}: {e}")
            continue
    
    # Sort by score descending
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches
