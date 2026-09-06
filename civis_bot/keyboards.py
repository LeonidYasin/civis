#!/usr/bin/env python3
"""
Keyboard layouts for Civis bot.
"""

from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from locales import TEXTS

def get_language_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(KeyboardButton("English"), KeyboardButton("Русский"))
    return keyboard

def get_main_keyboard(lang='en'):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = ["/offer", "/request", "/marketplace", "/profile", "/embedding", "/citizens", "/match", "/subscribe", "/help"]
    for b in buttons:
        keyboard.add(KeyboardButton(b))
    return keyboard

def get_values_keyboard(lang='en'):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    from utils import get_value_buttons
    for v in get_value_buttons(lang):
        keyboard.add(KeyboardButton(v))
    keyboard.add(KeyboardButton(TEXTS[lang]['done_button']))
    return keyboard

def get_roles_keyboard(lang='en'):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    from utils import get_roles
    for r in get_roles(lang):
        keyboard.add(KeyboardButton(r))
    return keyboard

def get_formats_keyboard(lang='en'):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    from utils import get_formats
    for f in get_formats(lang):
        keyboard.add(KeyboardButton(f))
    return keyboard

def get_subscribe_keyboard(lang='en'):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💳 Subscribe Premium - $9.99/mo", callback_data="subscribe_premium"),
        InlineKeyboardButton("🌟 Lifetime - $99 one-time", callback_data="subscribe_lifetime"),
        InlineKeyboardButton("🔑 Set API Key", callback_data="setkey")
    )
    return keyboard
