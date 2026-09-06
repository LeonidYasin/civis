#!/usr/bin/env python3
"""
Survey handlers for Civis bot.
Handles the multi-step registration process.
"""

import logging

from telebot.types import Message, ReplyKeyboardRemove

from database import get_user, get_session, set_session, clear_session, save_user, create_subscription
from locales import TEXTS, VALUE_MAP
from keyboards import get_main_keyboard, get_values_keyboard, get_roles_keyboard, get_formats_keyboard
from utils import get_text

logger = logging.getLogger(__name__)

# Global bot reference
bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

def handle_survey(message: Message):
    """Handle survey states - natural conversation"""
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
    
    # --- BACK BUTTON HANDLING ---
    if text == "/back" or text == "Назад" or text == "Back":
        if state == 'survey_about':
            set_session(tg_id, 'survey_name', {'language': lang, 'name': data.get('name', '')})
            bot.reply_to(message, TEXTS[lang]['name_ask'])
            return
        elif state == 'survey_values':
            set_session(tg_id, 'survey_about', {'language': lang, 'name': data.get('name', ''), 'about_text': data.get('about_text', '')})
            bot.reply_to(message, TEXTS[lang]['about_ask'])
            return
        elif state == 'survey_role':
            set_session(tg_id, 'survey_values', {
                'language': lang,
                'name': data.get('name', ''),
                'about_text': data.get('about_text', ''),
                'selected_values': data.get('selected_values', []),
                'user_values': data.get('user_values', '')
            })
            bot.reply_to(
                message,
                TEXTS[lang]['values_ask'],
                reply_markup=get_values_keyboard(lang)
            )
            return
        elif state == 'survey_format':
            set_session(tg_id, 'survey_role', {
                'language': lang,
                'name': data.get('name', ''),
                'about_text': data.get('about_text', ''),
                'selected_values': data.get('selected_values', []),
                'user_values': data.get('user_values', ''),
                'role': data.get('role', '')
            })
            bot.reply_to(message, TEXTS[lang]['role_ask'], reply_markup=get_roles_keyboard(lang))
            return
        else:
            bot.reply_to(message, "Can't go back from here.")
            return
    
    if state == 'survey_name':
        if len(text) < 2:
            bot.reply_to(message, "Please enter a valid name (at least 2 characters).")
            return
        data['name'] = text
        set_session(tg_id, 'survey_about', data)
        bot.reply_to(
            message,
            f"Nice to meet you, {text}! 👋\n\n" + TEXTS[lang]['about_ask'] + "\n\nSend /back to go back."
        )
    
    elif state == 'survey_about':
        if len(text) < 20:
            bot.reply_to(message, TEXTS[lang]['about_short'])
            return
        data['about_text'] = text
        data['selected_values'] = []
        set_session(tg_id, 'survey_values', data)
        bot.reply_to(
            message,
            TEXTS[lang]['values_intro'] + "\n\n" + TEXTS[lang]['values_ask'] + "\n\nSend /back to go back.",
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
                    ) + "\n\nSend /back to go back.",
                    reply_markup=get_values_keyboard(lang)
                )
            else:
                bot.reply_to(message, TEXTS[lang]['values_complete'], reply_markup=ReplyKeyboardRemove())
                data['user_values'] = ', '.join(selected)
                set_session(tg_id, 'survey_role', data)
                bot.reply_to(
                    message,
                    TEXTS[lang]['role_ask'] + "\n\nSend /back to go back.",
                    reply_markup=get_roles_keyboard(lang)
                )
        else:
            bot.reply_to(message, f"Please choose a value from the buttons.\n\nCurrent selection: {len(selected)}/3")
    
    elif state == 'survey_role':
        roles = ["Executor", "Customer", "Coordinator", "Investor", "Seller", "Buyer"]
        valid_roles = ["Executor", "Customer", "Coordinator", "Investor", "Seller", "Buyer"]
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
            if text not in valid_roles:
                bot.reply_to(
                    message,
                    f"Please select a role from the buttons: {', '.join(valid_roles)}"
                )
                return
            data['role'] = text
        
        set_session(tg_id, 'survey_format', data)
        bot.reply_to(
            message,
            TEXTS[lang]['format_ask'] + "\n\nSend /back to go back.",
            reply_markup=get_formats_keyboard(lang)
        )
    
    elif state == 'survey_format':
        if lang == 'ru':
            formats = ["Текст", "Голос", "Видео", "Любой"]
        else:
            formats = ["Text", "Voice", "Video", "Any"]
        
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
        from database import save_offer
        save_offer(tg_id, text)
        lang = get_user(tg_id).get('language', 'en')
        bot.reply_to(
            message,
            get_text(tg_id, 'offer_saved') + "\n\n" + get_text(tg_id, 'welcome_citizen', name=get_user(tg_id).get('name', '')),
            reply_markup=get_main_keyboard(lang)
        )
        clear_session(tg_id)
    
    elif state == 'request':
        from database import save_request
        save_request(tg_id, text)
        lang = get_user(tg_id).get('language', 'en')
        bot.reply_to(
            message,
            get_text(tg_id, 'request_saved') + "\n\n" + get_text(tg_id, 'welcome_citizen', name=get_user(tg_id).get('name', '')),
            reply_markup=get_main_keyboard(lang)
        )
        clear_session(tg_id)
