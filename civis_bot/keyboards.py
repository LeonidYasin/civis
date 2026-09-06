#!/usr/bin/env python3
"""
Keyboard layouts for Civis bot.
"""

from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from locales import TEXTS, get_value_buttons, get_roles, get_formats

def get_language_keyboard():
    """Language selection keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(KeyboardButton("English"), KeyboardButton("Русский"))
    return keyboard

def get_main_keyboard(lang='en'):
    """Main menu keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ["/offer", "/request", "/marketplace", "/profile", "/embedding", "/citizens", "/help"]
    for b in buttons:
        keyboard.add(KeyboardButton(b))
    return keyboard

def get_values_keyboard(lang='en'):
    """Values selection keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    for v in get_value_buttons(lang):
        keyboard.add(KeyboardButton(v))
    keyboard.add(KeyboardButton(TEXTS[lang]['done_button']))
    return keyboard

def get_roles_keyboard(lang='en'):
    """Roles selection keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for r in get_roles(lang):
        keyboard.add(KeyboardButton(r))
    return keyboard

def get_formats_keyboard(lang='en'):
    """Formats selection keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for f in get_formats(lang):
        keyboard.add(KeyboardButton(f))
    return keyboard
