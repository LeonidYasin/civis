#!/usr/bin/env python3
"""
Utility functions for Civis bot.
"""

import json
import logging

from locales import TEXTS
from database import get_user

logger = logging.getLogger(__name__)

def get_text(tg_id, key, **kwargs):
    """Get localized text for user"""
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    text = TEXTS.get(lang, TEXTS['en']).get(key, TEXTS['en'][key])
    return text.format(**kwargs) if kwargs else text

def get_embedding_profile(tg_id):
    """Generate a simple embedding profile text representation"""
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
