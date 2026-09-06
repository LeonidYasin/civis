#!/usr/bin/env python3
"""
Command handlers for Civis bot.
Contains all bot command handlers including subscription, AI key, and matching.
"""

import logging
import json
import requests
from datetime import datetime
from telebot.types import Message, ReplyKeyboardRemove

from database import (
    get_user, save_user, get_session, set_session, clear_session,
    get_all_citizens, get_all_offers, get_all_requests,
    get_my_offers, get_my_requests, save_offer, save_request,
    get_openai_key, save_openai_key,
    get_subscription, create_subscription, update_subscription_plan,
    can_use_match, get_matches_remaining, increment_matches_used
)
from locales import TEXTS, VALUE_MAP, get_value_buttons, get_roles, get_formats
from keyboards import (
    get_language_keyboard, get_main_keyboard, get_values_keyboard,
    get_roles_keyboard, get_formats_keyboard, get_subscribe_keyboard
)
from utils import get_text, get_embedding_profile, get_embedding, find_matches

logger = logging.getLogger(__name__)

# --- COMMAND HANDLERS ---

def cmd_start(message: Message, bot):
    tg_id = message.from_user.id
    username = message.from_user.username or "unknown"
    logger.info(f"Received /start from {tg_id}")
    
    user = get_user(tg_id)
    if user and user.get('status') == 'completed':
        lang = user.get('language', 'en')
        # Ensure subscription exists
        if not get_subscription(tg_id):
            create_subscription(tg_id)
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

def cmd_profile(message: Message, bot):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    sub = get_subscription(tg_id)
    matches_left = get_matches_remaining(tg_id)
    plan = sub.get('plan', 'free') if sub else 'free'
    
    profile_text = (
        f"{get_text(tg_id, 'profile')}\n\n"
        f"Name: {user.get('name', 'N/A')}\n"
        f"Telegram: @{user.get('username', 'N/A')}\n"
        f"Role: {user.get('role', 'N/A')}\n"
        f"Values: {user.get('user_values', 'N/A')}\n"
        f"Format: {user.get('format', 'N/A')}\n"
        f"Plan: {plan}\n"
        f"Matches left: {matches_left if matches_left != float('inf') else 'unlimited'}\n\n"
        f"About:\n{user.get('about_text', 'N/A')}"
    )
    bot.reply_to(message, profile_text)

def cmd_embedding(message: Message, bot):
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

def cmd_citizens(message: Message, bot):
    tg_id = message.from_user.id
    rows = get_all_citizens()
    if not rows:
        bot.reply_to(message, "No citizens yet. Be the first! Use /start to join.")
        return
    
    text = "👥 Citizens of Civis:\n\n"
    for username, name, role, values in rows:
        text += f"@{username or 'unknown'} - {name} ({role})\n   Values: {values}\n\n"
    bot.reply_to(message, text)

def cmd_offers(message: Message, bot):
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

def cmd_requests(message: Message, bot):
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

def cmd_my_offers(message: Message, bot):
    tg_id = message.from_user.id
    rows = get_my_offers(tg_id)
    if not rows:
        bot.reply_to(message, "You have no offers yet.")
        return
    
    text = "📦 Your Offers:\n\n"
    for id, offer_text, created_at in rows:
        text += f"ID {id}: {offer_text}\n\n"
    bot.reply_to(message, text)

def cmd_my_requests(message: Message, bot):
    tg_id = message.from_user.id
    rows = get_my_requests(tg_id)
    if not rows:
        bot.reply_to(message, "You have no requests yet.")
        return
    
    text = "📥 Your Requests:\n\n"
    for id, req_text, created_at in rows:
        text += f"ID {id}: {req_text}\n\n"
    bot.reply_to(message, text)

def cmd_marketplace(message: Message, bot):
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

def cmd_help(message: Message, bot):
    tg_id = message.from_user.id
    bot.reply_to(message, get_text(tg_id, 'help'))

def cmd_survey(message: Message, bot):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    set_session(tg_id, 'survey_name', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'name_ask'), reply_markup=ReplyKeyboardRemove())

def cmd_status(message: Message, bot):
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
            f"Proxy: {proxy_url or 'None'}"
        )
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

def cmd_cancel(message: Message, bot):
    tg_id = message.from_user.id
    clear_session(tg_id)
    bot.reply_to(message, get_text(tg_id, 'cancel'))

def cmd_done(message: Message, bot):
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

def cmd_offer(message: Message, bot):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'offer', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'offer_prompt'), reply_markup=ReplyKeyboardRemove())

def cmd_request(message: Message, bot):
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    set_session(tg_id, 'request', {'language': lang})
    bot.reply_to(message, get_text(tg_id, 'request_prompt'), reply_markup=ReplyKeyboardRemove())

# --- SUBSCRIPTION HANDLERS ---

def cmd_subscribe(message: Message, bot):
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
    
    current_plan = sub.get('plan', 'free')
    matches_left = get_matches_remaining(tg_id)
    
    text = f"""💳 **Civis Subscription Plans**

Current plan: **{current_plan}**
Matches remaining: **{matches_left if matches_left != float('inf') else 'unlimited'}**

---

**Free** - $0/month
- 3 AI matches per month
- Basic profile
- View citizens

**Premium** - $9.99/month
- Unlimited AI matches
- Priority in search results
- Export your profile
- Early access to new features

**Lifetime** - $99 one-time
- All Premium features
- Access to MCP tools
- Priority support

---

Click below to subscribe:"""
    
    bot.reply_to(
        message,
        text,
        parse_mode='Markdown',
        reply_markup=get_subscribe_keyboard(lang)
    )

# --- AI KEY HANDLER ---

def cmd_setkey(message: Message, bot):
    """Set OpenAI API key"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    # Check if key provided
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(
            message,
            "Please provide your OpenAI API key.\n"
            "Example: /setkey sk-...\n\n"
            "You can get a key from: https://platform.openai.com/api-keys"
        )
        return
    
    key = parts[1].strip()
    
    # Validate key (quick check)
    try:
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=10
        )
        if response.status_code != 200:
            bot.reply_to(message, "❌ Invalid API key. Please check and try again.")
            return
    except Exception as e:
        bot.reply_to(message, f"❌ Error validating key: {e}")
        return
    
    # Save key
    save_openai_key(tg_id, key)
    bot.reply_to(message, "✅ OpenAI API key saved successfully!")

# --- MATCH HANDLER ---

def cmd_match(message: Message, bot):
    """Find matches using AI"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    # Check if can use match
    if not can_use_match(tg_id):
        matches_left = get_matches_remaining(tg_id)
        bot.reply_to(
            message,
            f"❌ You've used all your free matches.\n"
            f"Remaining: {matches_left}\n\n"
            "Subscribe to get unlimited matches: /subscribe"
        )
        return
    
    # Get OpenAI key
    openai_key = get_openai_key(tg_id)
    if not openai_key:
        bot.reply_to(
            message,
            "❌ Please set your OpenAI API key first: /setkey sk-...\n\n"
            "You can get a key from: https://platform.openai.com/api-keys"
        )
        return
    
    # Get all citizens
    citizens = get_all_citizens()
    if not citizens:
        bot.reply_to(message, "No other citizens yet. Check back later!")
        return
    
    # Get current user's embedding
    my_embedding = get_embedding(user, openai_key)
    if not my_embedding:
        bot.reply_to(message, "❌ Error generating your profile embedding. Please try again.")
        return
    
    # Find matches
    matches = find_matches(my_embedding, citizens, openai_key)
    
    if not matches:
        bot.reply_to(message, "No matches found yet. Try updating your profile with more details!")
        return
    
    # Increment matches used
    increment_matches_used(tg_id)
    
    # Format results
    lang = user.get('language', 'en')
    text = f"🤝 **Your Top Matches**\n\n"
    
    for i, match in enumerate(matches[:5], 1):
        text += f"{i}. @{match.get('username', 'unknown')} - {match.get('name', 'Unknown')}\n"
        text += f"   Role: {match.get('role', 'N/A')}\n"
        text += f"   Values: {match.get('user_values', 'N/A')}\n"
        text += f"   Match score: {match.get('score', 0)}%\n\n"
    
    matches_left = get_matches_remaining(tg_id)
    text += f"\n---\nMatches remaining: {matches_left if matches_left != float('inf') else 'unlimited'}"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# --- SURVEY STATE HANDLERS (from bot_sync) ---

def handle_survey(message: Message, bot):
    """Handle survey states - natural conversation"""
    tg_id = message.from_user.id
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    state, data = get_session(tg_id)
    if not state or state == 'language_select':
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
            
            # Create subscription for new user
            create_subscription(tg_id)
            
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

# --- LANGUAGE SELECTION ---

def handle_language_selection(message: Message, bot):
    """Handle language selection"""
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
