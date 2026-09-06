#!/usr/bin/env python3
"""
Command handlers for Civis bot.
"""

import logging
from datetime import datetime

from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardRemove

from config import TOKEN
from database import (
    get_user, save_user, get_session, set_session, clear_session,
    get_all_citizens, get_all_offers, get_all_requests,
    get_my_offers, get_my_requests, save_offer, save_request
)
from keyboards import (
    get_language_keyboard, get_main_keyboard,
    get_values_keyboard, get_roles_keyboard, get_formats_keyboard
)
from locales import TEXTS, VALUE_MAP, get_value_buttons, get_roles, get_formats
from utils import get_text, get_embedding_profile

logger = logging.getLogger(__name__)

# --- COMMAND HANDLERS ---

def register_handlers(bot: TeleBot):
    """Register all command handlers with the bot"""
    
    @bot.message_handler(commands=['start'])
    def cmd_start(message: Message):
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

    @bot.message_handler(commands=['profile'])
    def cmd_profile(message: Message):
        tg_id = message.from_user.id
        user = get_user(tg_id)
        if not user or user.get('status') != 'completed':
            bot.reply_to(message, get_text(tg_id, 'no_profile'))
            return
        
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

    @bot.message_handler(commands=['embedding'])
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

    @bot.message_handler(commands=['citizens'])
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

    @bot.message_handler(commands=['offers'])
    def cmd_offers(message: Message):
        rows = get_all_offers()
        if not rows:
            bot.reply_to(message, "No offers yet. Use /offer to publish one!")
            return
        
        text = "📦 All Offers:\n\n"
        for tg_id, offer_text, _ in rows:
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"@{name}: {offer_text}\n\n"
        bot.reply_to(message, text)

    @bot.message_handler(commands=['requests'])
    def cmd_requests(message: Message):
        rows = get_all_requests()
        if not rows:
            bot.reply_to(message, "No requests yet. Use /request to publish one!")
            return
        
        text = "📥 All Requests:\n\n"
        for tg_id, req_text, _ in rows:
            user = get_user(tg_id)
            name = user.get('name', 'Unknown') if user else 'Unknown'
            text += f"@{name}: {req_text}\n\n"
        bot.reply_to(message, text)

    @bot.message_handler(commands=['my_offers'])
    def cmd_my_offers(message: Message):
        tg_id = message.from_user.id
        rows = get_my_offers(tg_id)
        if not rows:
            bot.reply_to(message, "You have no offers yet.")
            return
        
        text = "📦 Your Offers:\n\n"
        for offer_id, offer_text, _ in rows:
            text += f"ID {offer_id}: {offer_text}\n\n"
        bot.reply_to(message, text)

    @bot.message_handler(commands=['my_requests'])
    def cmd_my_requests(message: Message):
        tg_id = message.from_user.id
        rows = get_my_requests(tg_id)
        if not rows:
            bot.reply_to(message, "You have no requests yet.")
            return
        
        text = "📥 Your Requests:\n\n"
        for req_id, req_text, _ in rows:
            text += f"ID {req_id}: {req_text}\n\n"
        bot.reply_to(message, text)

    @bot.message_handler(commands=['marketplace'])
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

    @bot.message_handler(commands=['help'])
    def cmd_help(message: Message):
        bot.reply_to(message, get_text(message.from_user.id, 'help'))

    @bot.message_handler(commands=['survey'])
    def cmd_survey(message: Message):
        tg_id = message.from_user.id
        user = get_user(tg_id)
        lang = user.get('language', 'en') if user else 'en'
        set_session(tg_id, 'survey_name', {'language': lang})
        bot.reply_to(message, get_text(tg_id, 'name_ask'), reply_markup=ReplyKeyboardRemove())

    @bot.message_handler(commands=['status'])
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
            from config import get_proxy_url
            proxy_url = get_proxy_url()
            bot.reply_to(
                message,
                f"🤖 Civis Bot\n\n"
                f"Citizens: {count}\n"
                f"Offers: {offers_count}\n"
                f"Requests: {requests_count}\n"
                f"Proxy: {proxy_url or 'None'}"
            )
        except Exception as e:
            bot.reply_to(message, f"Error: {e}")

    @bot.message_handler(commands=['cancel'])
    def cmd_cancel(message: Message):
        tg_id = message.from_user.id
        clear_session(tg_id)
        bot.reply_to(message, get_text(tg_id, 'cancel'))

    @bot.message_handler(commands=['done'])
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
        bot.reply_to(
            message,
            TEXTS[lang]['values_complete'] + "\n\n" + TEXTS[lang]['role_ask'],
            reply_markup=get_roles_keyboard(lang)
        )

    @bot.message_handler(commands=['offer'])
    def cmd_offer(message: Message):
        tg_id = message.from_user.id
        user = get_user(tg_id)
        if not user or user.get('status') != 'completed':
            bot.reply_to(message, get_text(tg_id, 'no_profile'))
            return
        
        lang = user.get('language', 'en')
        set_session(tg_id, 'offer', {'language': lang})
        bot.reply_to(message, get_text(tg_id, 'offer_prompt'), reply_markup=ReplyKeyboardRemove())

    @bot.message_handler(commands=['request'])
    def cmd_request(message: Message):
        tg_id = message.from_user.id
        user = get_user(tg_id)
        if not user or user.get('status') != 'completed':
            bot.reply_to(message, get_text(tg_id, 'no_profile'))
            return
        
        lang = user.get('language', 'en')
        set_session(tg_id, 'request', {'language': lang})
        bot.reply_to(message, get_text(tg_id, 'request_prompt'), reply_markup=ReplyKeyboardRemove())

    @bot.message_handler(commands=['language'])
    def cmd_language(message: Message):
        tg_id = message.from_user.id
        logger.info(f"Received /language from {tg_id}")
        
        set_session(tg_id, 'language_select', {})
        bot.reply_to(
            message,
            "Choose your language:\n\nEnglish / Русский",
            reply_markup=get_language_keyboard()
        )

    # --- LANGUAGE SELECTION ---
    @bot.message_handler(func=lambda message: message.text in ["English", "Русский"])
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
    @bot.message_handler(func=lambda message: True, content_types=['text'])
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
            bot.reply_to(message, f"Nice to meet you, {text}!\n\n" + TEXTS[lang]['about_ask'])
        
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
            roles = get_roles(lang)
            if text not in roles:
                bot.reply_to(message, f"Please select a role from the buttons: {', '.join(roles)}")
                return
            
            data['role'] = text
            set_session(tg_id, 'survey_format', data)
            bot.reply_to(message, TEXTS[lang]['format_ask'], reply_markup=get_formats_keyboard(lang))
        
        elif state == 'survey_format':
            formats = get_formats(lang)
            if text not in formats:
                bot.reply_to(message, f"Please select a format from the buttons: {', '.join(formats)}")
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
            bot.reply_to(
                message,
                get_text(tg_id, 'offer_saved') + "\n\n" + get_text(tg_id, 'welcome_citizen', name=get_user(tg_id).get('name', '')),
                reply_markup=get_main_keyboard(lang)
            )
            clear_session(tg_id)
        
        elif state == 'request':
            save_request(tg_id, text)
            bot.reply_to(
                message,
                get_text(tg_id, 'request_saved') + "\n\n" + get_text(tg_id, 'welcome_citizen', name=get_user(tg_id).get('name', '')),
                reply_markup=get_main_keyboard(lang)
            )
            clear_session(tg_id)

    logger.info("All handlers registered")
