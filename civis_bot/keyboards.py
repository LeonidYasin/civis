#!/usr/bin/env python3
"""
Keyboard layouts for Civis bot.
"""

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from locales import TEXTS

def get_language_keyboard():
    """Language selection keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("English"),
        KeyboardButton("Русский")
    )
    return keyboard

def get_main_keyboard(lang='en'):
    """Main menu keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if lang == 'ru':
        keyboard.add(
            KeyboardButton("/offer"),
            KeyboardButton("/request"),
            KeyboardButton("/marketplace"),
            KeyboardButton("/profile"),
            KeyboardButton("/embedding"),
            KeyboardButton("/citizens"),
            KeyboardButton("/help"),
        )
    else:
        keyboard.add(
            KeyboardButton("/offer"),
            KeyboardButton("/request"),
            KeyboardButton("/marketplace"),
            KeyboardButton("/profile"),
            KeyboardButton("/embedding"),
            KeyboardButton("/citizens"),
            KeyboardButton("/help"),
        )
    return keyboard

def get_values_keyboard(lang='en'):
    """Values selection keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    if lang == 'ru':
        values = ["Честность", "Экспертиза", "Инициатива", "Надёжность", "Скорость", "Эмпатия", "Системность", "Креативность", "Открытость", "Амбициозность"]
    else:
        values = ["Honesty", "Expertise", "Initiative", "Reliability", "Speed", "Empathy", "Systematic", "Creativity", "Openness", "Ambition"]
    
    for v in values:
        keyboard.add(KeyboardButton(v))
    keyboard.add(KeyboardButton("/done"))
    return keyboard

def get_roles_keyboard(lang='en'):
    """Role selection keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if lang == 'ru':
        roles = ["Исполнитель", "Заказчик", "Координатор", "Инвестор", "Продавец", "Покупатель"]
    else:
        roles = ["Executor", "Customer", "Coordinator", "Investor", "Seller", "Buyer"]
    
    for r in roles:
        keyboard.add(KeyboardButton(r))
    return keyboard

def get_formats_keyboard(lang='en'):
    """Format selection keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if lang == 'ru':
        formats = ["Текст", "Голос", "Видео", "Любой"]
    else:
        formats = ["Text", "Voice", "Video", "Any"]
    
    for f in formats:
        keyboard.add(KeyboardButton(f))
    return keyboard
