#!/usr/bin/env python3
"""
Handlers for Civis bot commands.
"""

import logging
import json
from datetime import datetime

from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BotCommand

from database import (
    get_user, save_user, get_session, set_session, clear_session,
    get_all_citizens, get_my_offers, get_my_requests,
    get_all_offers, get_all_requests,
    save_offer, save_request, delete_offer, delete_request,
    get_subscription, create_subscription, update_subscription_plan,
    can_use_match, get_matches_remaining, increment_matches_used,
    get_openai_key, save_openai_key
)
from locales import TEXTS, VALUE_MAP
from keyboards import (
    get_main_keyboard, get_language_keyboard,
    get_values_keyboard, get_roles_keyboard, get_formats_keyboard
)
from utils import get_text, get_embedding_profile
from config import get_proxy_url

logger = logging.getLogger(__name__)

# Global bot reference (set in bot.py)
bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

# --- REGISTRATION HANDLERS ---

def register_handlers():
    """Register all command handlers with the bot"""
    if not bot:
        raise RuntimeError("Bot not set. Call set_bot() first.")
    
    # Command handlers
    bot.message_handler(commands=['start'])(cmd_start)
    bot.message_handler(commands=['profile'])(cmd_profile)
    bot.message_handler(commands=['embedding'])(cmd_embedding)
    bot.message_handler(commands=['citizens'])(cmd_citizens)
    bot.message_handler(commands=['offers'])(cmd_offers)
    bot.message_handler(commands=['requests'])(cmd_requests)
    bot.message_handler(commands=['my_offers'])(cmd_my_offers)
    bot.message_handler(commands=['my_requests'])(cmd_my_requests)
    bot.message_handler(commands=['marketplace'])(cmd_marketplace)
    bot.message_handler(commands=['help'])(cmd_help)
    bot.message_handler(commands=['survey'])(cmd_survey)
    bot.message_handler(commands=['status'])(cmd_status)
    bot.message_handler(commands=['cancel'])(cmd_cancel)
    bot.message_handler(commands=['done'])(cmd_done)
    bot.message_handler(commands=['offer'])(cmd_offer)
    bot.message_handler(commands=['request'])(cmd_request)
    bot.message_handler(commands=['language'])(cmd_language)
    bot.message_handler(commands=['subscribe'])(cmd_subscribe)
    bot.message_handler(commands=['setkey'])(cmd_setkey)
    bot.message_handler(commands=['match'])(cmd_match)
    
    # Language selection handler
    bot.message_handler(func=lambda m: m.text in ["English", "Русский"])(handle_language_selection)
    
    # Survey state handler
    bot.message_handler(func=lambda m: True, content_types=['text'])(handle_survey)
    
    logger.info("All handlers registered")

# --- COMMAND HANDLERS ---

def cmd_start(message: Message):
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    logger.info(f"Received /start from {tg_id}")
    
    user = get_user(tg_id)
    if user and user.get('status') == 'completed':
        lang = user.get('language', 'en')
        bot.reply_to(
            message,
            get_text(tg_id, 'welcome_citizen', name=user.get('name', 'friend')),
            reply_markup=get_main_keyboard(lang)
        )
        return
    
    set_session(tg_id, 'language_select', {})
    bot.reply_to(
        message,
        "Choose your language:\n\nEnglish / Русский",
        reply_markup=get_language_keyboard()
    )

def cmd_profile(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    profile_text = (
        f"{get_text(tg_id, 'profile')}\n\n"
        f"Name: {user.get('name', 'N/A')}\n"
        f"Telegram: @{user.get('username', 'N/A')}\n"
        f"Role: {user.get('role', 'N/A')}\n"
        f"Values: {user.get('user_values', 'N/A')}\n"
        f"Format: {user.get('format', 'N/A')}\n\n"
        f"About:\n{user.get('about_text', 'N/A')}"
    )
    bot.reply_to(message, profile_text)

def cmd_embedding(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    embed_profile = get_embedding_profile(tg_id)
    bot.reply_to(
        message,
        f"🧠 Your Embedding Profile:\n\n```json\n{embed_profile}\n```\n\nThis is your AI-compatible profile for matching.",
        parse_mode='Markdown'
    )

def cmd_citizens(message: Message):
    tg_id = message.from_user.id
    rows = get_all_citizens()
    if not rows:
        bot.reply_to(message, "No citizens yet. Be the first! Use /start to join.")
        return
    
    text = "👥 Citizens of Civis:\n\n"
    for username, name, role, values in rows:
        text += f"@{username or 'unknown'} - {name} ({role})\n   Values: {values}\n\n"
    bot.reply_to(message, text)

def cmd_offers(message: Message):
    rows = get_all_offers()
    if not rows:
        bot.reply_to(message, "No offers yet. Use /offer to publish one!")
        return
    
    text = "📦 All Offers:\n\n"
    for tg_id, offer_text, created_at in rows:
        user = get_user(tg_id)
        name = user.get('name', 'Unknown') if user else 'Unknown'
        text += f"@{name}: {offer_text}\n\n"
    bot.reply_to(message, text)

def cmd_requests(message: Message):
    rows = get_all_requests()
    if not rows:
        bot.reply_to(message, "No requests yet. Use /request to publish one!")
        return
    
    text = "📥 All Requests:\n\n"
    for tg_id, req_text, created_at in rows:
        user = get_user(tg_id)
        name = user.get('name', 'Unknown') if user else 'Unknown'
        text += f"@{name}: {req_text}\n\n"
    bot.reply_to(message, text)

def cmd_my_offers(message: Message):
    tg_id = message.from_user.id
    rows = get_my_offers(tg_id)
    if not rows:
        bot.reply_to(message, "You have no offers yet.")
        return
    
    text = "📦 Your Offers:\n\n"
    for id, offer_text, created_at in rows:
        text += f"ID {id}: {offer_text}\n\n"
    bot.reply_to(message, text)

def cmd_my_requests(message: Message):
    tg_id = message.from_user.id
    rows = get_my_requests(tg_id)
    if not rows:
        bot.reply_to(message, "You have no requests yet.")
        return
    
    text = "📥 Your Requests:\n\n"
    for id, req_text, created_at in rows:
        text += f"ID {id}: {req_text}\n\n"
    bot.reply_to(message, text)

def cmd_marketplace(message: Message):
    tg_id = message.from_user.id
    offers = get_all_offers()
    requests = get_all_requests()
    
    text = "🛒 Marketplace:\n\n"
    text += "📦 Offers:\n"
    if offers:
        for tg_id, offer_text, _ in offers[:5]:
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  - {name}: {offer_text}\n"
    else:
        text += "  (none)\n"
    
    text += "\n📥 Requests:\n"
    if requests:
        for tg_id, req_text, _ in requests[:5]:
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  - {name}: {req_text}\n"
    else:
        text += "  (none)\n"
    
    bot.reply_to(message, text)

def cmd_help(message: Message):
    bot.reply_to(message, get_text(message.from_user.id, 'help'))

def cmd_survey(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    set_session(tg_id, 'survey_name', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'name_ask'), reply_markup=ReplyKeyboardRemove())

def cmd_status(message: Message):
    tg_id = message.from_user.id
    try:
        me = bot.get_me()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE status = 'completed'")
        count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM offers")
        offers_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM requests")
        requests_count = cur.fetchone()[0]
        conn.close()
        bot.reply_to(
            message,
            f"🤖 Civis Bot\n\n"
            f"Citizens: {count}\n"
            f"Offers: {offers_count}\n"
            f"Requests: {requests_count}\n"
            f"Proxy: {get_proxy_url() or 'None'}"
        )
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

def cmd_cancel(message: Message):
    tg_id = message.from_user.id
    clear_session(tg_id)
    bot.reply_to(message, get_text(tg_id, 'cancel'))

def cmd_done(message: Message):
    tg_id = message.from_user.id
    state, data = get_session(tg_id)
    if state != 'survey_values':
        bot.reply_to(message, "You're not in value selection mode.")
        return
    
    selected = data.get('selected_values', [])
    if len(selected) != 3:
        lang = data.get('language', 'en')
        remaining = 3 - len(selected)
        bot.reply_to(message, TEXTS[lang]['values_error'].format(count=len(selected), remaining=remaining))
        return
    
    lang = data.get('language', 'en')
    data['user_values'] = ', '.join(selected)
    set_session(tg_id, 'survey_role', data)
    bot.reply_to(message, TEXTS[lang]['values_complete'] + "\n\n" + TEXTS[lang]['role_ask'], reply_markup=get_roles_keyboard(lang))

def cmd_offer(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'offer_prompt'), reply_markup=ReplyKeyboardRemove())

def cmd_request(message: Message):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'request', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'request_prompt'), reply_markup=ReplyKeyboardRemove())

def cmd_language(message: Message):
    tg_id = message.from_user.id
    logger.info(f"Received /language from {tg_id}")
    
    set_session(tg_id, 'language_select', {})
    bot.reply_to(
        message,
        "Choose your language:\n\nEnglish / Русский",
        reply_markup=get_language_keyboard()
    )

def cmd_subscribe(message: Message):
    """Show subscription plans"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    sub = get_subscription(tg_id)
    if not sub:
        create_subscription(tg_id)
        sub = get_subscription(tg_id)
    
    remaining = get_matches_remaining(tg_id)
    
    text = f"""💳 **Subscription Plans**

Current plan: {sub['plan'].upper()}
Matches remaining: {remaining if remaining != float('inf') else '∞'}

📌 **Free** — $0/month
  • 3 matches/month
  • Basic profile
  • View citizens

⭐ **Premium** — $9.99/month
  • Unlimited matches
  • Priority in search
  • Export profile (JSON)
  • Early access to new features

🚀 **Lifetime** — $99 one-time
  • All Premium features
  • MCP tools access
  • Lifetime updates

To upgrade, send /setkey to use your own OpenAI key, or contact @civis_support for payment."""
    bot.reply_to(message, text, parse_mode='Markdown')

def cmd_setkey(message: Message):
    """Set OpenAI API key"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(
            message,
            "Please provide your OpenAI API key:\n"
            "`/setkey sk-...`\n\n"
            "You can get your key at: https://platform.openai.com/api-keys"
        )
        return
    
    key = parts[1]
    if not key.startswith('sk-') or len(key) < 20:
        bot.reply_to(message, "❌ Invalid OpenAI key format. It should start with 'sk-'. Please check and try again.")
        return
    
    save_openai_key(tg_id, key)
    bot.reply_to(message, "✅ OpenAI key saved successfully! You can now use /match for AI-powered matching.")

def cmd_match(message: Message):
    """AI-powered matching"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    openai_key = get_openai_key(tg_id)
    if not openai_key:
        bot.reply_to(
            message,
            "❌ You need to set your OpenAI API key first.\n"
            "Use `/setkey sk-...` to set your key."
        )
        return
    
    if not can_use_match(tg_id):
        remaining = get_matches_remaining(tg_id)
        bot.reply_to(
            message,
            f"❌ You've used all your free matches.\n"
            f"Remaining: {remaining}\n"
            "Use `/subscribe` to upgrade to Premium."
        )
        return
    
    increment_matches_used(tg_id)
    
    citizens = get_all_citizens()
    if not citizens:
        bot.reply_to(message, "No citizens to match with yet. Come back later!")
        return
    
    user_profile = f"""Name: {user.get('name', 'Unknown')}
Role: {user.get('role', 'N/A')}
Values: {user.get('user_values', 'N/A')}
About: {user.get('about_text', 'N/A')}"""
    
    citizens_list = []
    for username, name, role, values in citizens:
        if tg_id != get_user_by_username(username):
            citizens_list.append(f"@{username} - {name} ({role})")
    
    if not citizens_list:
        bot.reply_to(message, "No other citizens to match with yet. Share the bot with friends!")
        return
    
    bot.reply_to(
        message,
        f"🔍 AI Matching in progress...\n\n"
        f"Your profile:\n{user_profile}\n\n"
        f"We're analyzing {len(citizens_list)} other citizens.\n"
        f"Full AI matching coming soon!"
    )

def get_user_by_username(username):
    """Helper to get user by username"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tg_id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

# --- LANGUAGE SELECTION ---

def handle_language_selection(message: Message):
    tg_id = message.from_user.id
    text = message.text
    
    lang = 'en' if text == "English" else 'ru'
    
    user = get_user(tg_id)
    if user:
        save_user(tg_id, user.get('username', 'unknown'), language=lang)
    else:
        save_user(tg_id, message.from_user.username or "unknown", language=lang)
    
    state, _ = get_session(tg_id)
    if state == 'language_select':
        clear_session(tg_id)
    
    user = get_user(tg_id)
    if user and user.get('status') == 'completed':
        bot.reply_to(
            message,
            TEXTS[lang]['language_changed'] + "\n\n" + TEXTS[lang]['welcome_citizen'].format(name=user.get('name', '')),
            reply_markup=get_main_keyboard(lang)
        )
    else:
        bot.reply_to(
            message,
            TEXTS[lang]['language_set'] + "\n\n" + TEXTS[lang]['welcome'],
            reply_markup=ReplyKeyboardRemove()
        )
        
        set_session(tg_id, 'survey_name', {'language': lang})
        bot.send_message(tg_id, TEXTS[lang]['name_ask'])

# --- SURVEY HANDLERS ---

def handle_survey(message: Message):
    tg_id = message.from_user.id
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    state, data = get_session(tg_id)
    if not state:
        lang = get_user(tg_id).get('language', 'en') if get_user(tg_id) else 'en'
        bot.reply_to(message, get_text(tg_id, 'unknown'), reply_markup=get_main_keyboard(lang))
        return
    
    lang = data.get('language', 'en')
    
    if state == 'survey_name':
        if len(text) < 2:
            bot.reply_to(message, "Please enter a valid name (at least 2 characters).")
            return
        data['name'] = text
        set_session(tg_id, 'survey_about', data)
        bot.reply_to(message, f"Nice to meet you, {text}! 👋\n\n" + TEXTS[lang]['about_ask'])
    
    elif state == 'survey_about':
        if len(text) < 20:
            bot.reply_to(message, TEXTS[lang]['about_short'])
            return
        data['about_text'] = text
        data['selected_values'] = []
        set_session(tg_id, 'survey_values', data)
        bot.reply_to(
            message,
            TEXTS[lang]['values_intro'] + "\n\n" + TEXTS[lang]['values_ask'],
            reply_markup=get_values_keyboard(lang)
        )
    
    elif state == 'survey_values':
        value_map = VALUE_MAP.get(lang, VALUE_MAP['en'])
        selected = data.get('selected_values', [])
        
        valid_value = None
        if text in value_map:
            valid_value = value_map[text]
        elif text in VALUE_MAP['en']:
            valid_value = text
        elif text in VALUE_MAP['ru']:
            valid_value = VALUE_MAP['ru'][text]
        
        if valid_value and valid_value not in selected:
            selected.append(valid_value)
            data['selected_values'] = selected
            set_session(tg_id, 'survey_values', data)
            
            remaining = 3 - len(selected)
            if remaining > 0:
                bot.reply_to(
                    message,
                    TEXTS[lang]['values_selected'].format(
                        values=', '.join(selected),
                        remaining=remaining
                    ),
                    reply_markup=get_values_keyboard(lang)
                )
            else:
                bot.reply_to(message, TEXTS[lang]['values_complete'], reply_markup=ReplyKeyboardRemove())
                data['user_values'] = ', '.join(selected)
                set_session(tg_id, 'survey_role', data)
                bot.reply_to(message, TEXTS[lang]['role_ask'], reply_markup=get_roles_keyboard(lang))
        else:
            bot.reply_to(message, f"Please choose a value from the buttons.\n\nCurrent selection: {len(selected)}/3")
    
    elif state == 'survey_role':
        if lang == 'ru':
            ru_roles = ["Исполнитель", "Заказчик", "Координатор", "Инвестор", "Продавец", "Покупатель"]
            if text in ru_roles:
                role_map = {
                    "Исполнитель": "Executor",
                    "Заказчик": "Customer",
                    "Координатор": "Coordinator",
                    "Инвестор": "Investor",
                    "Продавец": "Seller",
                    "Покупатель": "Buyer"
                }
                data['role'] = role_map[text]
            else:
                bot.reply_to(
                    message,
                    f"Пожалуйста, выберите роль из кнопок: {', '.join(ru_roles)}"
                )
                return
        else:
            valid_roles = ["Executor", "Customer", "Coordinator", "Investor", "Seller", "Buyer"]
            if text not in valid_roles:
                bot.reply_to(
                    message,
                    f"Please select a role from the buttons: {', '.join(valid_roles)}"
                )
                return
            data['role'] = text
        
        set_session(tg_id, 'survey_format', data)
        bot.reply_to(message, TEXTS[lang]['format_ask'], reply_markup=get_formats_keyboard(lang))
    
    elif state == 'survey_format':
        if lang == 'ru':
            ru_formats = ["Текст", "Голос", "Видео", "Любой"]
            if text in ru_formats:
                # Store English value
                format_map = {
                    "Текст": "Text",
                    "Голос": "Voice",
                    "Видео": "Video",
                    "Любой": "Any"
                }
                data['format'] = format_map[text]
            else:
                bot.reply_to(
                    message,
                    f"Пожалуйста, выберите формат из кнопок: {', '.join(ru_formats)}"
                )
                return
        else:
            valid_formats = ["Text", "Voice", "Video", "Any"]
            if text not in valid_formats:
                bot.reply_to(
                    message,
                    f"Please select a format from the buttons: {', '.join(valid_formats)}"
                )
                return
            data['format'] = text
        
        username = message.from_user.username or "unknown"
        
        try:
            save_user(
                tg_id=tg_id,
                username=username,
                name=data.get('name', ''),
                telegram_contact=f"@{username}",
                about_text=data.get('about_text', ''),
                user_values=data.get('user_values', ''),
                role=data.get('role', ''),
                format=data.get('format', ''),
                language=lang,
                status='completed'
            )
            
            clear_session(tg_id)
            
            create_subscription(tg_id)
            
            bot.reply_to(
                message,
                TEXTS[lang]['profile_complete'] + "\n\n" + TEXTS[lang]['welcome_citizen'].format(name=data.get('name', '')),
                reply_markup=get_main_keyboard(lang)
            )
            
            logger.info(f"Profile completed for {tg_id}: {data.get('name')}")
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            bot.reply_to(message, "Error saving your profile. Please try again.")
    
    elif state == 'offer':
        save_offer(tg_id, text)
        lang = get_user(tg_id).get('language', 'en')
        bot.reply_to(
            message,
            get_text(tg_id, 'offer_saved') + "\n\n" + get_text(tg_id, 'welcome_citizen', name=get_user(tg_id).get('name', '')),
            reply_markup=get_main_keyboard(lang)
        )
        clear_session(tg_id)
    
    elif state == 'request':
        save_request(tg_id, text)
        lang = get_user(tg_id).get('language', 'en')
        bot.reply_to(
            message,
            get_text(tg_id, 'request_saved') + "\n\n" + get_text(tg_id, 'welcome_citizen', name=get_user(tg_id).get('name', '')),
            reply_markup=get_main_keyboard(lang)
        )
        clear_session(tg_id)
