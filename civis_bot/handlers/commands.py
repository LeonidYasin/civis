#!/usr/bin/env python3
"""
Command handlers for Civis bot.
"""

import logging
import sqlite3

from telebot.types import Message, ReplyKeyboardRemove

from database import (
    get_user, save_user, get_session, set_session, clear_session,
    get_all_citizens, get_my_offers, get_my_requests,
    get_all_offers, get_all_requests,
    save_offer, save_request, delete_offer, delete_request,
    get_subscription, create_subscription,
    can_use_match, get_matches_remaining, increment_matches_used,
    get_openai_key, save_openai_key, search_citizens, DB_PATH
)
from locales import TEXTS
from keyboards import (
    get_main_keyboard, get_language_keyboard,
    get_values_keyboard, get_roles_keyboard, get_formats_keyboard
)
from utils import get_text, get_embedding_profile, find_matches, generate_match_explanation, get_profile_text
from config import get_proxy_url, ADMIN_CHAT_ID

from .survey import handle_survey, set_bot as set_survey_bot
from .language import handle_language_selection, set_bot as set_language_bot

logger = logging.getLogger(__name__)

# Global bot reference (set in bot.py)
bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance
    set_survey_bot(bot_instance)
    set_language_bot(bot_instance)

def log_message(message: Message, prefix=""):
    """Helper to log message details"""
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    chat_type = message.chat.type
    chat_id = message.chat.id
    text = message.text or ""
    logger.info(f"{prefix} msg from {tg_id} (@{username}) in {chat_type} (chat_id={chat_id}): {text[:50]}")
    if chat_type in ['group', 'supergroup']:
        logger.info(f"[GROUP] chat_id={chat_id}, title={message.chat.title or 'N/A'}")

# --- REGISTRATION ---

def register_handlers():
    """Register all command handlers with the bot"""
    if not bot:
        raise RuntimeError("Bot not set. Call set_bot() first.")
    
    # Register handlers
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
    bot.message_handler(commands=['search'])(cmd_search)
    bot.message_handler(commands=['delete_offer'])(cmd_delete_offer)
    bot.message_handler(commands=['delete_request'])(cmd_delete_request)
    bot.message_handler(commands=['support'])(cmd_support)
    
    # Language selection handler
    bot.message_handler(func=lambda m: m.text in ["English", "Русский"])(handle_language_selection)
    
    # Survey state handler (catch-all for text messages)
    bot.message_handler(func=lambda m: True, content_types=['text'])(handle_survey)
    
    logger.info("All handlers registered")

# --- COMMAND HANDLERS ---

def cmd_start(message: Message):
    log_message(message, "[CMD]")
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
    log_message(message, "[CMD]")
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
    log_message(message, "[CMD]")
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
    log_message(message, "[CMD]")
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
    log_message(message, "[CMD]")
    rows = get_all_offers()
    if not rows:
        bot.reply_to(message, "No offers yet. Use /offer to publish one!")
        return
    
    text = "📦 All Offers:\n\n"
    for row in rows:
        if len(row) == 5:
            id, tg_id, category, offer_text, created_at = row
        else:
            tg_id, offer_text, created_at = row
            id = '?'
            category = 'general'
        user = get_user(tg_id)
        name = user.get('name', 'Unknown') if user else 'Unknown'
        text += f"ID {id} [{category}] - @{name}: {offer_text}\n\n"
    bot.reply_to(message, text)

def cmd_requests(message: Message):
    log_message(message, "[CMD]")
    rows = get_all_requests()
    if not rows:
        bot.reply_to(message, "No requests yet. Use /request to publish one!")
        return
    
    text = "📥 All Requests:\n\n"
    for row in rows:
        if len(row) == 5:
            id, tg_id, category, req_text, created_at = row
        else:
            tg_id, req_text, created_at = row
            id = '?'
            category = 'general'
        user = get_user(tg_id)
        name = user.get('name', 'Unknown') if user else 'Unknown'
        text += f"ID {id} [{category}] - @{name}: {req_text}\n\n"
    bot.reply_to(message, text)

def cmd_my_offers(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    rows = get_my_offers(tg_id)
    if not rows:
        bot.reply_to(message, "You have no offers yet.")
        return
    
    text = "📦 Your Offers:\n\n"
    for id, category, offer_text, created_at in rows:
        text += f"ID {id} [{category}]: {offer_text}\n"
        text += f"To delete: /delete_offer {id}\n\n"
    bot.reply_to(message, text)

def cmd_my_requests(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    rows = get_my_requests(tg_id)
    if not rows:
        bot.reply_to(message, "You have no requests yet.")
        return
    
    text = "📥 Your Requests:\n\n"
    for id, category, req_text, created_at in rows:
        text += f"ID {id} [{category}]: {req_text}\n"
        text += f"To delete: /delete_request {id}\n\n"
    bot.reply_to(message, text)

def cmd_delete_offer(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /delete_offer <id>\n\nUse /my_offers to see your offers with IDs.")
        return
    
    try:
        offer_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Invalid ID. Please provide a number.")
        return
    
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    if delete_offer(offer_id, tg_id):
        bot.reply_to(message, f"✅ Offer #{offer_id} deleted successfully.")
    else:
        bot.reply_to(message, f"❌ Offer #{offer_id} not found or you don't have permission to delete it.")

def cmd_delete_request(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /delete_request <id>\n\nUse /my_requests to see your requests with IDs.")
        return
    
    try:
        req_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Invalid ID. Please provide a number.")
        return
    
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    if delete_request(req_id, tg_id):
        bot.reply_to(message, f"✅ Request #{req_id} deleted successfully.")
    else:
        bot.reply_to(message, f"❌ Request #{req_id} not found or you don't have permission to delete it.")

def cmd_marketplace(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    offers = get_all_offers()
    requests = get_all_requests()
    
    text = "🛒 Marketplace:\n\n"
    text += "📦 Offers:\n"
    if offers:
        for row in offers[:5]:
            if len(row) == 5:
                id, tg_id, category, offer_text, _ = row
            else:
                tg_id, offer_text, _ = row
                id = '?'
                category = 'general'
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  - #{id} [{category}] {name}: {offer_text}\n"
    else:
        text += "  (none)\n"
    
    text += "\n📥 Requests:\n"
    if requests:
        for row in requests[:5]:
            if len(row) == 5:
                id, tg_id, category, req_text, _ = row
            else:
                tg_id, req_text, _ = row
                id = '?'
                category = 'general'
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"  - #{id} [{category}] {name}: {req_text}\n"
    else:
        text += "  (none)\n"
    
    bot.reply_to(message, text)

def cmd_help(message: Message):
    log_message(message, "[CMD]")
    bot.reply_to(message, get_text(message.from_user.id, 'help'))

def cmd_survey(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    set_session(tg_id, 'survey_name', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'name_ask'), reply_markup=ReplyKeyboardRemove())

def cmd_status(message: Message):
    log_message(message, "[CMD]")
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
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    clear_session(tg_id)
    bot.reply_to(message, get_text(tg_id, 'cancel'))

def cmd_done(message: Message):
    log_message(message, "[CMD]")
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
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'offer_prompt'), reply_markup=ReplyKeyboardRemove())

def cmd_request(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'request', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'request_prompt'), reply_markup=ReplyKeyboardRemove())

def cmd_language(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    logger.info(f"Received /language from {tg_id}")
    
    set_session(tg_id, 'language_select', {})
    bot.reply_to(
        message,
        "Choose your language:\n\nEnglish / Русский",
        reply_markup=get_language_keyboard()
    )

def cmd_subscribe(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    
    user = get_user(tg_id)
    if not user:
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    if user.get('status') != 'completed':
        bot.reply_to(message, "Your profile is not complete. Use /start to complete it!")
        return
    
    lang = user.get('language', 'en')
    sub = get_subscription(tg_id)
    if not sub:
        create_subscription(tg_id)
        sub = get_subscription(tg_id)
    
    remaining = get_matches_remaining(tg_id)
    remaining_text = str(remaining) if remaining != float('inf') else '∞'
    
    text = f"""{get_text(tg_id, 'subscribe_title')}

{get_text(tg_id, 'subscribe_current', plan=sub['plan'].upper())}
{get_text(tg_id, 'subscribe_remaining', remaining=remaining_text)}

{get_text(tg_id, 'subscribe_free')}

{get_text(tg_id, 'subscribe_premium')}

{get_text(tg_id, 'subscribe_lifetime')}

{get_text(tg_id, 'subscribe_upgrade')}"""
    bot.reply_to(message, text)

def cmd_setkey(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, get_text(tg_id, 'setkey_prompt'))
        return
    
    key = parts[1]
    if not key.startswith('sk-') or len(key) < 20:
        bot.reply_to(message, get_text(tg_id, 'setkey_invalid'))
        return
    
    save_openai_key(tg_id, key)
    bot.reply_to(message, get_text(tg_id, 'setkey_saved'))

def cmd_match(message: Message):
    """AI-powered matching - REAL implementation"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    # Check if OpenAI key is set
    openai_key = get_openai_key(tg_id)
    if not openai_key:
        bot.reply_to(
            message,
            get_text(tg_id, 'setkey_required'),
            parse_mode='Markdown'
        )
        return
    
    # Check subscription
    if not can_use_match(tg_id):
        remaining = get_matches_remaining(tg_id)
        bot.reply_to(
            message,
            get_text(tg_id, 'match_limit_exceeded', remaining=remaining)
        )
        return
    
    # Send "thinking" message
    thinking_msg = bot.reply_to(message, "🔍 Analyzing your profile and finding matches...")
    
    try:
        # Find matches using AI
        matches = find_matches(tg_id, openai_key, limit=5)
        
        if matches is None:
            bot.edit_message_text(
                "❌ Error generating your profile embedding. Please try again later.",
                chat_id=thinking_msg.chat.id,
                message_id=thinking_msg.message_id
            )
            return
        
        if not matches:
            bot.edit_message_text(
                "🤔 No matches found yet. Try updating your profile with more details!\n\n"
                "Use `/survey` to update your profile.",
                chat_id=thinking_msg.chat.id,
                message_id=thinking_msg.message_id
            )
            return
        
        # Increment matches used
        increment_matches_used(tg_id)
        remaining = get_matches_remaining(tg_id)
        remaining_text = str(remaining) if remaining != float('inf') else '∞'
        
        # Build results with explanations
        lang = user.get('language', 'en')
        text = f"🤝 **Your Top Matches**\n\n"
        
        for i, match in enumerate(matches, 1):
            explanation = generate_match_explanation(user, match)
            text += f"{i}. **{match['name']}** (@{match['username']})\n"
            text += f"   🎯 Match score: {match['score']}%\n"
            text += f"   💼 Role: {match['role']}\n"
            text += f"   💎 Values: {match['values']}\n"
            text += f"   📝 {explanation}\n\n"
        
        # Add footer with remaining matches
        if remaining_text != '∞':
            text += f"\n---\n📊 Matches remaining this month: **{remaining_text}**\n"
        else:
            text += f"\n---\n⭐ Premium plan — unlimited matches!"
        
        text += "\n\n💡 Use `/survey` to update your profile for better matches."
        
        bot.edit_message_text(
            text,
            chat_id=thinking_msg.chat.id,
            message_id=thinking_msg.message_id,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Match error: {e}")
        bot.edit_message_text(
            f"❌ Error during matching: {str(e)}\n\nPlease try again later.",
            chat_id=thinking_msg.chat.id,
            message_id=thinking_msg.message_id
        )

def cmd_search(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /search <text>\n\nSearch for citizens by name, role, or values.")
        return
    
    query = ' '.join(parts[1:])
    results = search_citizens(query)
    
    if not results:
        bot.reply_to(message, f"No citizens found matching '{query}'.")
        return
    
    text = f"🔍 Search results for '{query}':\n\n"
    for username, name, role, values, about in results[:20]:
        text += f"@{username or 'unknown'} - {name}\n"
        text += f"Role: {role}\nValues: {values}\n"
        if about:
            text += f"About: {about[:100]}...\n"
        text += "\n"
    
    if len(results) > 20:
        text += f"... and {len(results) - 20} more results."
    
    bot.reply_to(message, text)

def cmd_support(message: Message):
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    set_session(tg_id, 'support', {'language': user.get('language', 'en')})
    bot.reply_to(message, get_text(tg_id, 'support_prompt'))

def get_user_by_username(username):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT tg_id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
