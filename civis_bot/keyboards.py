#!/usr/bin/env python3
"""
Keyboard layouts for Civis bot.
Using InlineKeyboardMarkup for interactive buttons and ReplyKeyboardMarkup for input helpers.
"""

from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
import time
import threading
from collections import OrderedDict


class BoundedClickTracker:
    """Thread-safe bounded in-memory sliding window click tracker."""
    def __init__(self, max_size: int = 1000, window_seconds: float = 1.0):
        self._max_size = max_size
        self._window_seconds = window_seconds
        self._clicks = OrderedDict()  # (user_id, action_prefix) -> timestamp
        self._lock = threading.Lock()

    def is_throttled(self, user_id: int, action: str) -> bool:
        now = time.time()
        key = (user_id, action)
        with self._lock:
            if len(self._clicks) > self._max_size:
                cutoff = now - (self._window_seconds * 10)
                old_keys = [k for k, ts in self._clicks.items() if ts < cutoff]
                for k in old_keys:
                    del self._clicks[k]
                if len(self._clicks) > self._max_size:
                    self._clicks.popitem(last=False)

            last_ts = self._clicks.get(key)
            if last_ts and (now - last_ts) < self._window_seconds:
                return True
            self._clicks[key] = now
            return False

    def clear(self):
        with self._lock:
            self._clicks.clear()


CLICK_TRACKER = BoundedClickTracker()


def get_empty_items_keyboard(prefix: str, lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for empty offers/requests list."""
    markup = InlineKeyboardMarkup()
    act_cb = "act:offer" if prefix == "o" else "act:request"
    act_label = "➕ Создать предложение" if prefix == "o" else "➕ Создать запрос"
    markup.row(
        InlineKeyboardButton(act_label, callback_data=act_cb),
        InlineKeyboardButton("🏬 Маркетплейс", callback_data="hub:mkt")
    )
    return markup


def get_item_card_keyboard(prefix: str, item_id: int, current_page: int, total_pages: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for single item view with pagination (1 item per page)."""
    markup = InlineKeyboardMarkup()
    prev_cb = f"pg:{prefix}:{current_page - 1}" if current_page > 1 else "noop"
    next_cb = f"pg:{prefix}:{current_page + 1}" if current_page < total_pages else "noop"
    markup.row(
        InlineKeyboardButton("◀", callback_data=prev_cb),
        InlineKeyboardButton(f"[ {current_page} / {total_pages} ]", callback_data="noop"),
        InlineKeyboardButton("▶", callback_data=next_cb)
    )
    markup.row(
        InlineKeyboardButton("🗑 Удалить", callback_data=f"ask_del:{prefix}:{item_id}:{current_page}")
    )
    act_cb = "act:offer" if prefix == "o" else "act:request"
    act_label = "➕ Создать" if prefix == "o" else "➕ Создать"
    markup.row(
        InlineKeyboardButton(act_label, callback_data=act_cb),
        InlineKeyboardButton("🏬 Маркетплейс", callback_data="hub:mkt")
    )
    return markup


def get_delete_confirm_keyboard(prefix: str, item_id: int, current_page: int, lang: str = "ru") -> InlineKeyboardMarkup:
    """Confirmation dialog keyboard for deleting an item."""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Да, удалить", callback_data=f"cfm_del:{prefix}:{item_id}:{current_page}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"cxl_del:{prefix}:{item_id}:{current_page}")
    )
    return markup


def get_language_keyboard():
    """Language selection - 2 columns"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(
        KeyboardButton("English"),
        KeyboardButton("Русский")
    )
    return keyboard

def get_main_keyboard(lang='en'):
    """Main menu - ReplyKeyboard for quick commands (not full, just most used)"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    
    if lang == 'ru':
        keyboard.row(
            KeyboardButton("/offer"),
            KeyboardButton("/request")
        )
        keyboard.row(
            KeyboardButton("/my_offers"),
            KeyboardButton("/my_requests")
        )
        keyboard.row(
            KeyboardButton("/marketplace"),
            KeyboardButton("/profile")
        )
        keyboard.row(
            KeyboardButton("/subscribe"),
            KeyboardButton("/match")
        )
        keyboard.row(
            KeyboardButton("/language"),
            KeyboardButton("/help")
        )
        keyboard.row(
            KeyboardButton("/menu")
        )
    else:
        keyboard.row(
            KeyboardButton("/offer"),
            KeyboardButton("/request")
        )
        keyboard.row(
            KeyboardButton("/my_offers"),
            KeyboardButton("/my_requests")
        )
        keyboard.row(
            KeyboardButton("/marketplace"),
            KeyboardButton("/profile")
        )
        keyboard.row(
            KeyboardButton("/subscribe"),
            KeyboardButton("/match")
        )
        keyboard.row(
            KeyboardButton("/language"),
            KeyboardButton("/help")
        )
        keyboard.row(
            KeyboardButton("/menu")
        )
    
    return keyboard

def get_inline_main_keyboard(lang='en'):
    """Main menu as inline buttons (execute immediately on click) - FULL list"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if lang == 'ru':
        # Profile & Account
        keyboard.add(
            InlineKeyboardButton("👤 Профиль", callback_data="profile"),
            InlineKeyboardButton("🧠 Эмбеддинг", callback_data="embedding")
        )
        # Marketplace
        keyboard.add(
            InlineKeyboardButton("📤 Предложить", callback_data="offer"),
            InlineKeyboardButton("📥 Запросить", callback_data="request")
        )
        keyboard.add(
            InlineKeyboardButton("🏠 Недвижимость", callback_data="offer_real_estate"),
            InlineKeyboardButton("🚕 Такси", callback_data="offer_taxi")
        )
        keyboard.add(
            InlineKeyboardButton("📦 Доставка", callback_data="offer_delivery"),
            InlineKeyboardButton("🛒 Маркетплейс", callback_data="marketplace")
        )
        # My items
        keyboard.add(
            InlineKeyboardButton("📦 Мои предложения", callback_data="my_offers"),
            InlineKeyboardButton("📋 Мои запросы", callback_data="my_requests")
        )
        keyboard.add(
            InlineKeyboardButton("🗑 Удалить предложение", callback_data="delete_offer"),
            InlineKeyboardButton("🗑 Удалить запрос", callback_data="delete_request")
        )
        # People & Search
        keyboard.add(
            InlineKeyboardButton("👥 Граждане", callback_data="citizens"),
            InlineKeyboardButton("🔍 Поиск", callback_data="search")
        )
        keyboard.add(
            InlineKeyboardButton("🎯 Матчинг", callback_data="match"),
            InlineKeyboardButton("💳 Подписка", callback_data="subscribe")
        )
        # Settings & Help
        keyboard.add(
            InlineKeyboardButton("🌐 Язык", callback_data="language"),
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        )
        keyboard.add(
            InlineKeyboardButton("📩 Поддержка", callback_data="support"),
            InlineKeyboardButton("📋 Меню", callback_data="menu")
        )
        keyboard.add(
            InlineKeyboardButton("🏠 Старт", callback_data="start")
        )
    else:
        # Profile & Account
        keyboard.add(
            InlineKeyboardButton("👤 Profile", callback_data="profile"),
            InlineKeyboardButton("🧠 Embedding", callback_data="embedding")
        )
        # Marketplace
        keyboard.add(
            InlineKeyboardButton("📤 Offer", callback_data="offer"),
            InlineKeyboardButton("📥 Request", callback_data="request")
        )
        keyboard.add(
            InlineKeyboardButton("🏠 Real Estate", callback_data="offer_real_estate"),
            InlineKeyboardButton("🚕 Taxi", callback_data="offer_taxi")
        )
        keyboard.add(
            InlineKeyboardButton("📦 Delivery", callback_data="offer_delivery"),
            InlineKeyboardButton("🛒 Marketplace", callback_data="marketplace")
        )
        # My items
        keyboard.add(
            InlineKeyboardButton("📦 My Offers", callback_data="my_offers"),
            InlineKeyboardButton("📋 My Requests", callback_data="my_requests")
        )
        keyboard.add(
            InlineKeyboardButton("🗑 Delete Offer", callback_data="delete_offer"),
            InlineKeyboardButton("🗑 Delete Request", callback_data="delete_request")
        )
        # People & Search
        keyboard.add(
            InlineKeyboardButton("👥 Citizens", callback_data="citizens"),
            InlineKeyboardButton("🔍 Search", callback_data="search")
        )
        keyboard.add(
            InlineKeyboardButton("🎯 Match", callback_data="match"),
            InlineKeyboardButton("💳 Subscribe", callback_data="subscribe")
        )
        # Settings & Help
        keyboard.add(
            InlineKeyboardButton("🌐 Language", callback_data="language"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        )
        keyboard.add(
            InlineKeyboardButton("📩 Support", callback_data="support"),
            InlineKeyboardButton("📋 Menu", callback_data="menu")
        )
        keyboard.add(
            InlineKeyboardButton("🏠 Start", callback_data="start")
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
