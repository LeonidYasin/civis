#!/usr/bin/env python3
"""
Keyboard layouts for Civis bot.
Using InlineKeyboardMarkup for interactive buttons and ReplyKeyboardMarkup for input helpers.
"""

from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

def get_language_keyboard():
    """Language selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("English"),
        KeyboardButton("Русский")
    )
    return keyboard

def get_main_keyboard(lang='en'):
    """Main menu - ReplyKeyboard for quick commands"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    keyboard.row(
        KeyboardButton("/offer"),
        KeyboardButton("/request")
    )
    keyboard.row(
        KeyboardButton("/my_offers"),
        KeyboardButton("/my_requests")
    )
    keyboard.row(
        KeyboardButton("/delete_offer"),
        KeyboardButton("/delete_request")
    )
    keyboard.row(
        KeyboardButton("/marketplace"),
        KeyboardButton("/profile")
    )
    keyboard.row(
        KeyboardButton("/embedding"),
        KeyboardButton("/citizens")
    )
    keyboard.row(
        KeyboardButton("/subscribe"),
        KeyboardButton("/match")
    )
    keyboard.row(
        KeyboardButton("/search"),
        KeyboardButton("/help")
    )
    keyboard.row(
        KeyboardButton("/support")
    )
    
    return keyboard

def get_inline_main_keyboard(lang='en', with_icons=False):
    """Main menu as inline buttons (execute immediately on click)"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if with_icons:
        # With icons for visual menu
        keyboard.add(
            InlineKeyboardButton("📤 Offer", callback_data="offer"),
            InlineKeyboardButton("📥 Request", callback_data="request")
        )
        keyboard.add(
            InlineKeyboardButton("📦 My Offers", callback_data="my_offers"),
            InlineKeyboardButton("📋 My Requests", callback_data="my_requests")
        )
        keyboard.add(
            InlineKeyboardButton("🗑 Delete Offer", callback_data="delete_offer"),
            InlineKeyboardButton("🗑 Delete Request", callback_data="delete_request")
        )
        keyboard.add(
            InlineKeyboardButton("🛒 Marketplace", callback_data="marketplace"),
            InlineKeyboardButton("👤 Profile", callback_data="profile")
        )
        keyboard.add(
            InlineKeyboardButton("🧠 Embedding", callback_data="embedding"),
            InlineKeyboardButton("👥 Citizens", callback_data="citizens")
        )
        keyboard.add(
            InlineKeyboardButton("💳 Subscribe", callback_data="subscribe"),
            InlineKeyboardButton("🎯 Match", callback_data="match")
        )
        keyboard.add(
            InlineKeyboardButton("🔍 Search", callback_data="search"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        )
        keyboard.add(
            InlineKeyboardButton("📩 Support", callback_data="support")
        )
    else:
        # Clean buttons without icons
        keyboard.add(
            InlineKeyboardButton("Offer", callback_data="offer"),
            InlineKeyboardButton("Request", callback_data="request")
        )
        keyboard.add(
            InlineKeyboardButton("My Offers", callback_data="my_offers"),
            InlineKeyboardButton("My Requests", callback_data="my_requests")
        )
        keyboard.add(
            InlineKeyboardButton("Delete Offer", callback_data="delete_offer"),
            InlineKeyboardButton("Delete Request", callback_data="delete_request")
        )
        keyboard.add(
            InlineKeyboardButton("Marketplace", callback_data="marketplace"),
            InlineKeyboardButton("Profile", callback_data="profile")
        )
        keyboard.add(
            InlineKeyboardButton("Embedding", callback_data="embedding"),
            InlineKeyboardButton("Citizens", callback_data="citizens")
        )
        keyboard.add(
            InlineKeyboardButton("Subscribe", callback_data="subscribe"),
            InlineKeyboardButton("Match", callback_data="match")
        )
        keyboard.add(
            InlineKeyboardButton("Search", callback_data="search"),
            InlineKeyboardButton("Help", callback_data="help")
        )
        keyboard.add(
            InlineKeyboardButton("Support", callback_data="support")
        )
    
    return keyboard

def get_category_keyboard(lang='en'):
    """Category selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    if lang == 'ru':
        keyboard.row(
            KeyboardButton("Общее"),
            KeyboardButton("Такси")
        )
        keyboard.row(
            KeyboardButton("Доставка"),
            KeyboardButton("Услуги")
        )
        keyboard.row(
            KeyboardButton("Товары"),
            KeyboardButton("Недвижимость")
        )
        keyboard.row(
            KeyboardButton("Другое")
        )
        keyboard.row(
            KeyboardButton("/cancel")
        )
    else:
        keyboard.row(
            KeyboardButton("General"),
            KeyboardButton("Taxi")
        )
        keyboard.row(
            KeyboardButton("Delivery"),
            KeyboardButton("Services")
        )
        keyboard.row(
            KeyboardButton("Goods"),
            KeyboardButton("Real Estate")
        )
        keyboard.row(
            KeyboardButton("Other")
        )
        keyboard.row(
            KeyboardButton("/cancel")
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
    
    keyboard.row(
        KeyboardButton(values[0]),
        KeyboardButton(values[1]),
        KeyboardButton(values[2])
    )
    keyboard.row(
        KeyboardButton(values[3]),
        KeyboardButton(values[4]),
        KeyboardButton(values[5])
    )
    keyboard.row(
        KeyboardButton(values[6]),
        KeyboardButton(values[7]),
        KeyboardButton(values[8])
    )
    keyboard.row(
        KeyboardButton(values[9])
    )
    keyboard.row(
        KeyboardButton("/done")
    )
    keyboard.row(
        KeyboardButton("/back")
    )
    
    return keyboard

def get_roles_keyboard(lang='en'):
    """Role selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    if lang == 'ru':
        roles = ["Исполнитель", "Заказчик", "Координатор", "Инвестор", "Продавец", "Покупатель"]
    else:
        roles = ["Executor", "Customer", "Coordinator", "Investor", "Seller", "Buyer"]
    
    keyboard.row(
        KeyboardButton(roles[0]),
        KeyboardButton(roles[1])
    )
    keyboard.row(
        KeyboardButton(roles[2]),
        KeyboardButton(roles[3])
    )
    keyboard.row(
        KeyboardButton(roles[4]),
        KeyboardButton(roles[5])
    )
    keyboard.row(
        KeyboardButton("/back")
    )
    
    return keyboard

def get_formats_keyboard(lang='en'):
    """Format selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    if lang == 'ru':
        formats = ["Текст", "Голос", "Видео", "Любой"]
    else:
        formats = ["Text", "Voice", "Video", "Any"]
    
    keyboard.row(
        KeyboardButton(formats[0]),
        KeyboardButton(formats[1])
    )
    keyboard.row(
        KeyboardButton(formats[2]),
        KeyboardButton(formats[3])
    )
    keyboard.row(
        KeyboardButton("/back")
    )
    
    return keyboard
