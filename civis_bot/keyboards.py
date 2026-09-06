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
    """Main menu - 2 columns with support button"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    # Row 1: Create
    keyboard.row(
        KeyboardButton("/offer"),
        KeyboardButton("/request")
    )
    # Row 2: Real Estate
    keyboard.row(
        KeyboardButton("/offer_real_estate"),
        KeyboardButton("/request_real_estate")
    )
    # Row 3: View own
    keyboard.row(
        KeyboardButton("/my_offers"),
        KeyboardButton("/my_requests")
    )
    # Row 4: Delete
    keyboard.row(
        KeyboardButton("/delete_offer"),
        KeyboardButton("/delete_request")
    )
    # Row 5: Marketplace & Profile
    keyboard.row(
        KeyboardButton("/marketplace"),
        KeyboardButton("/profile")
    )
    # Row 6: Embedding & Citizens
    keyboard.row(
        KeyboardButton("/embedding"),
        KeyboardButton("/citizens")
    )
    # Row 7: Subscribe & Match
    keyboard.row(
        KeyboardButton("/subscribe"),
        KeyboardButton("/match")
    )
    # Row 8: Search & Help
    keyboard.row(
        KeyboardButton("/search"),
        KeyboardButton("/help")
    )
    # Row 9: Support (full width)
    keyboard.row(
        KeyboardButton("/support")
    )
    
    return keyboard

def get_category_keyboard(lang='en'):
    """Category selection for offers/requests - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    if lang == 'ru':
        keyboard.row(
            KeyboardButton("Общее"),
            KeyboardButton("Недвижимость")
        )
        keyboard.row(
            KeyboardButton("Такси"),
            KeyboardButton("Доставка")
        )
        keyboard.row(
            KeyboardButton("Услуги"),
            KeyboardButton("Товары")
        )
        keyboard.row(
            KeyboardButton("Другое"),
            KeyboardButton("/cancel")
        )
    else:
        keyboard.row(
            KeyboardButton("General"),
            KeyboardButton("Real Estate")
        )
        keyboard.row(
            KeyboardButton("Taxi"),
            KeyboardButton("Delivery")
        )
        keyboard.row(
            KeyboardButton("Services"),
            KeyboardButton("Goods")
        )
        keyboard.row(
            KeyboardButton("Other"),
            KeyboardButton("/cancel")
        )
    
    return keyboard

def get_property_type_keyboard(lang='en'):
    """Property type selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    if lang == 'ru':
        keyboard.row(
            KeyboardButton("Квартира"),
            KeyboardButton("Дом")
        )
        keyboard.row(
            KeyboardButton("Коммерческая"),
            KeyboardButton("Земельный участок")
        )
        keyboard.row(
            KeyboardButton("Любой"),
            KeyboardButton("/cancel")
        )
    else:
        keyboard.row(
            KeyboardButton("Apartment"),
            KeyboardButton("House")
        )
        keyboard.row(
            KeyboardButton("Commercial"),
            KeyboardButton("Land")
        )
        keyboard.row(
            KeyboardButton("Any"),
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
    # Row 6 - Back button
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
    # Row 4 - Back button
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
    # Row 3 - Back button
    keyboard.row(
        KeyboardButton("/back")
    )
    
    return keyboard
