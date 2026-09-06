#!/usr/bin/env python3
"""
Keyboard layouts for Civis bot.
Using keyboard.row() for explicit row control.
"""

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def get_language_keyboard():
    """Language selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("English"),
        KeyboardButton("Русский")
    )
    return keyboard

def get_main_keyboard(lang='en'):
    """Main menu - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    # Row 1
    keyboard.row(
        KeyboardButton("/offer"),
        KeyboardButton("/request")
    )
    # Row 2
    keyboard.row(
        KeyboardButton("/marketplace"),
        KeyboardButton("/profile")
    )
    # Row 3
    keyboard.row(
        KeyboardButton("/embedding"),
        KeyboardButton("/citizens")
    )
    # Row 4
    keyboard.row(
        KeyboardButton("/subscribe"),
        KeyboardButton("/match")
    )
    # Row 5
    keyboard.row(
        KeyboardButton("/help")
    )
    
    return keyboard

def get_values_keyboard(lang='en'):
    """Values selection - 3 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
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
    
    # Row 1
    keyboard.row(
        KeyboardButton(values[0]),
        KeyboardButton(values[1]),
        KeyboardButton(values[2])
    )
    # Row 2
    keyboard.row(
        KeyboardButton(values[3]),
        KeyboardButton(values[4]),
        KeyboardButton(values[5])
    )
    # Row 3
    keyboard.row(
        KeyboardButton(values[6]),
        KeyboardButton(values[7]),
        KeyboardButton(values[8])
    )
    # Row 4
    keyboard.row(
        KeyboardButton(values[9])
    )
    # Row 5 - Done button
    keyboard.row(
        KeyboardButton("/done")
    )
    
    return keyboard

def get_roles_keyboard(lang='en'):
    """Role selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    if lang == 'ru':
        roles = ["Исполнитель", "Заказчик", "Координатор", "Инвестор", "Продавец", "Покупатель"]
    else:
        roles = ["Executor", "Customer", "Coordinator", "Investor", "Seller", "Buyer"]
    
    # Row 1
    keyboard.row(
        KeyboardButton(roles[0]),
        KeyboardButton(roles[1])
    )
    # Row 2
    keyboard.row(
        KeyboardButton(roles[2]),
        KeyboardButton(roles[3])
    )
    # Row 3
    keyboard.row(
        KeyboardButton(roles[4]),
        KeyboardButton(roles[5])
    )
    
    return keyboard

def get_formats_keyboard(lang='en'):
    """Format selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    if lang == 'ru':
        formats = ["Текст", "Голос", "Видео", "Любой"]
    else:
        formats = ["Text", "Voice", "Video", "Any"]
    
    # Row 1
    keyboard.row(
        KeyboardButton(formats[0]),
        KeyboardButton(formats[1])
    )
    # Row 2
    keyboard.row(
        KeyboardButton(formats[2]),
        KeyboardButton(formats[3])
    )
    
    return keyboard
