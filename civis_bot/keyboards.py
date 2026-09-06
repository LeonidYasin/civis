#!/usr/bin/env python3
"""
Keyboard layouts for Civis bot.
All keyboards use row_width to display buttons in multiple columns.
"""

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def get_language_keyboard():
    """Language selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        row_width=2
    )
    keyboard.add(
        KeyboardButton("English"),
        KeyboardButton("Русский")
    )
    return keyboard

def get_main_keyboard(lang='en'):
    """Main menu - 2 columns for mobile comfort"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        row_width=2
    )
    
    # Group commands in pairs
    buttons = [
        "/offer", "/request",
        "/marketplace", "/profile",
        "/embedding", "/citizens",
        "/subscribe", "/match",
        "/help"
    ]
    
    for b in buttons:
        keyboard.add(KeyboardButton(b))
    
    return keyboard

def get_values_keyboard(lang='en'):
    """Values selection - 3 columns (10 items = 4 rows, last row has 2 items)"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        row_width=3
    )
    
    if lang == 'ru':
        values = [
            "Честность", "Экспертиза", "Инициатива",
            "Надёжность", "Скорость", "Эмпатия",
            "Системность", "Креативность", "Открытость",
            "Амбициозность"
        ]
    else:
        values = [
            "Honesty", "Expertise", "Initiative",
            "Reliability", "Speed", "Empathy",
            "Systematic", "Creativity", "Openness",
            "Ambition"
        ]
    
    for v in values:
        keyboard.add(KeyboardButton(v))
    
    # Done button as separate row
    keyboard.add(KeyboardButton("/done"))
    
    return keyboard

def get_roles_keyboard(lang='en'):
    """Role selection - 2 columns (6 items = 3 rows)"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        row_width=2
    )
    
    if lang == 'ru':
        roles = [
            "Исполнитель", "Заказчик",
            "Координатор", "Инвестор",
            "Продавец", "Покупатель"
        ]
    else:
        roles = [
            "Executor", "Customer",
            "Coordinator", "Investor",
            "Seller", "Buyer"
        ]
    
    for r in roles:
        keyboard.add(KeyboardButton(r))
    
    return keyboard

def get_formats_keyboard(lang='en'):
    """Format selection - 2 columns (4 items = 2 rows)"""
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        row_width=2
    )
    
    if lang == 'ru':
        formats = ["Текст", "Голос", "Видео", "Любой"]
    else:
        formats = ["Text", "Voice", "Video", "Any"]
    
    for f in formats:
        keyboard.add(KeyboardButton(f))
    
    return keyboard
