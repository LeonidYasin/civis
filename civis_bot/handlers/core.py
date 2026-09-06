#!/usr/bin/env python3
"""
Core command handlers for Civis bot.
Contains: start, menu, profile, embedding, citizens, help, survey, status, cancel, done, language, reload
"""

import logging
import sqlite3
import os
import sys

from telebot.types import Message, ReplyKeyboardRemove

from database import (
    get_user, save_user, get_session, set_session, clear_session,
    get_all_citizens, DB_PATH
)
from locales import TEXTS
from keyboards import (
    get_main_keyboard, get_language_keyboard,
    get_values_keyboard, get_roles_keyboard, get_formats_keyboard,
    get_inline_main_keyboard
)
from utils import get_text, get_embedding_profile
from config import get_proxy_url

from .helpers import log_message, get_bot

logger = logging.getLogger(__name__)

# --- COMMAND HANDLERS ---

def cmd_start(message: Message):
    bot = get_bot()
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
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

def cmd_menu(message: Message):
    """Show full main menu with all commands as inline buttons"""
    bot = get_bot()
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    
    # Full command list
    text = "📋 **Civis Bot — Full Menu**\n\n"
    text += "**Profile & Account**\n"
    text += "`/start` — Create or view your profile\n"
    text += "`/profile` — View your profile\n"
    text += "`/survey` — Update your profile\n"
    text += "`/embedding` — View AI embedding profile\n\n"
    
    text += "**Marketplace**\n"
    text += "`/offer` — Publish an offer (with category)\n"
    text += "`/offer_real_estate` — Quick real estate offer\n"
    text += "`/offer_taxi` — Quick taxi offer\n"
    text += "`/offer_delivery` — Quick delivery offer\n"
    text += "`/request` — Publish a request\n"
    text += "`/my_offers` — View your offers\n"
    text += "`/my_requests` — View your requests\n"
    text += "`/delete_offer <id>` — Delete your offer\n"
    text += "`/delete_request <id>` — Delete your request\n"
    text += "`/marketplace` — View marketplace\n"
    text += "`/offers` — View all offers\n"
    text += "`/requests` — View all requests\n\n"
    
    text += "**People & Search**\n"
    text += "`/citizens` — List all citizens\n"
    text += "`/search <text>` — Search citizens\n"
    text += "`/match` — AI-powered matching\n\n"
    
    text += "**Subscriptions & AI**\n"
    text += "`/subscribe` — View subscription plans\n"
    text += "`/setkey <key>` — Set OpenAI API key\n"
    text += "`/upload_dialog` — Upload dialog history\n"
    text += "`/my_dialogs` — List uploaded dialogs\n"
    text += "`/process_dialogs` — Process dialogs\n\n"
    
    text += "**Settings & Help**\n"
    text += "`/language` — Change language\n"
    text += "`/support` — Contact developer\n"
    text += "`/status` — Bot status\n"
    text += "`/help` — Help\n"
    text += "`/cancel` — Cancel current operation\n"
    text += "`/done` — Finish value selection\n"
    
    # Use inline keyboard for interactive menu (buttons execute immediately)
    bot.reply_to(
        message,
        text,
        parse_mode='Markdown',
        reply_markup=get_inline_main_keyboard(lang)
    )

def cmd_reload(message: Message):
    """Reload the bot (admin only)"""
    bot = get_bot()
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    
    # Admin check (only Leonid can reload)
    if tg_id != 521254540:
        bot.reply_to(message, "⛔ Admin only command.")
        return
    
    bot.reply_to(message, "🔄 Reloading bot...")
    logger.info("Reloading bot...")
    
    # Graceful restart
    try:
        # Stop polling
        bot.stop_polling()
        # Restart the process
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        logger.error(f"Reload error: {e}")
        bot.reply_to(message, f"❌ Reload error: {e}")

def cmd_profile(message: Message):
    bot = get_bot()
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
    bot = get_bot()
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
    bot = get_bot()
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

def cmd_help(message: Message):
    bot = get_bot()
    log_message(message, "[CMD]")
    bot.reply_to(message, get_text(message.from_user.id, 'help'))

def cmd_survey(message: Message):
    bot = get_bot()
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    set_session(tg_id, 'survey_name', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'name_ask'), reply_markup=ReplyKeyboardRemove())

def cmd_status(message: Message):
    bot = get_bot()
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
    bot = get_bot()
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    clear_session(tg_id)
    bot.reply_to(message, get_text(tg_id, 'cancel'))

def cmd_done(message: Message):
    bot = get_bot()
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

def cmd_language(message: Message):
    bot = get_bot()
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    logger.info(f"Received /language from {tg_id}")
    
    set_session(tg_id, 'language_select', {})
    bot.reply_to(
        message,
        "Choose your language:\n\nEnglish / Русский",
        reply_markup=get_language_keyboard()
    )
