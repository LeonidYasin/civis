#!/usr/bin/env python3
"""
Keyboard layouts for Civis bot.
Optimized for mobile-friendly tile display with appropriate column counts.
"""

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from locales import TEXTS

def get_language_keyboard():
    """Language selection keyboard - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("English"),
        KeyboardButton("Русский")
    )
    return keyboard

def get_main_keyboard(lang='en'):
    """Main menu keyboard - 2 columns for better visibility"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Commands in logical groups
    buttons = [
        "/offer",      # Publish offer
        "/request",    # Publish request
        "/marketplace", # View marketplace
        "/profile",    # My profile
        "/embedding",  # Embedding profile
        "/citizens",   # View citizens
        "/subscribe",  # Subscription plans
        "/match",      # AI matching
        "/help",       # Help
    ]
    
    for b in buttons:
        keyboard.add(KeyboardButton(b))
    
    return keyboard

def get_values_keyboard(lang='en'):
    """Values selection keyboard - 3 columns for 10 values (optimal 4 rows)"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    if lang == 'ru':
        values = ["Честность", "Экспертиза", "Инициатива", "Надёжность", "Скорость", "Эмпатия", "Системность", "Креативность", "Открытость", "Амбициозность"]
    else:
        values = ["Honesty", "Expertise", "Initiative", "Reliability", "Speed", "Empathy", "Systematic", "Creativity", "Openness", "Ambition"]
    
    for v in values:
        keyboard.add(KeyboardButton(v))
    
    # Add done button in its own row
    keyboard.add(KeyboardButton("/done"))
    
    return keyboard

def get_roles_keyboard(lang='en'):
    """Role selection keyboard - 2 columns for 6 roles (3 rows)"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if lang == 'ru':
        roles = ["Исполнитель", "Заказчик", "Координатор", "Инвестор", "Продавец", "Покупатель"]
    else:
        roles = ["Executor", "Customer", "Coordinator", "Investor", "Seller", "Buyer"]
    
    for r in roles:
        keyboard.add(KeyboardButton(r))
    
    return keyboard

def get_formats_keyboard(lang='en'):
    """Format selection keyboard - 2 columns for 4 formats (2 rows)"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if lang == 'ru':
        formats = ["Текст", "Голос", "Видео", "Любой"]
    else:
        formats = ["Text", "Voice", "Video", "Any"]
    
    for f in formats:
        keyboard.add(KeyboardButton(f))
    
    return keyboard
