#!/usr/bin/env python3
"""
Real estate handlers for Civis bot.
Handles property listings and AI matching.
"""

import logging
from telebot.types import Message
from database import (
    get_user, get_session, set_session, clear_session,
    save_offer, save_request, get_all_offers, get_all_requests,
    find_matching_offers_for_request, find_matching_requests_for_offer
)
from keyboards import get_main_keyboard
from utils import get_text

logger = logging.getLogger(__name__)

# Global bot reference
bot = None

def set_bot(bot_instance):
    global bot
    bot = bot_instance

def handle_real_estate_survey(message: Message):
    """Handle real estate specific survey states"""
    if bot is None:
        logger.error("Bot not set in real_estate.py!")
        return
    
    tg_id = message.from_user.id
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    state, data = get_session(tg_id)
    if not state or not state.startswith('real_estate_'):
        return
    
    user = get_user(tg_id)
    lang = user.get('language', 'en') if user else 'en'
    
    # --- OFFER FLOW ---
    if state == 'real_estate_offer_type':
        # Save property type
        property_types = ["Apartment", "House", "Commercial", "Land", "Other"]
        ru_types = ["Квартира", "Дом", "Коммерческая", "Земельный участок", "Другое"]
        
        if lang == 'ru':
            if text not in ru_types:
                bot.reply_to(message, f"Пожалуйста, выберите тип недвижимости из кнопок: {', '.join(ru_types)}")
                return
            # Map to English for storage
            type_map = dict(zip(ru_types, property_types))
            data['property_type'] = type_map[text]
        else:
            if text not in property_types:
                bot.reply_to(message, f"Please select property type: {', '.join(property_types)}")
                return
            data['property_type'] = text
        
        set_session(tg_id, 'real_estate_offer_price', data)
        bot.reply_to(message, "💰 Enter the price (in USD):\n\nOr type '0' for 'negotiable'")
    
    elif state == 'real_estate_offer_price':
        try:
            data['price'] = int(text)
        except ValueError:
            if text.lower() in ['negotiable', 'договорная', '0']:
                data['price'] = None
            else:
                bot.reply_to(message, "Please enter a valid number (e.g., 150000) or type 'negotiable'")
                return
        
        set_session(tg_id, 'real_estate_offer_area', data)
        bot.reply_to(message, "📐 Enter the area (in square meters):")
    
    elif state == 'real_estate_offer_area':
        try:
            data['area'] = int(text)
            if data['area'] <= 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "Please enter a valid positive number for area.")
            return
        
        set_session(tg_id, 'real_estate_offer_rooms', data)
        bot.reply_to(message, "🛏️ Enter number of rooms:")
    
    elif state == 'real_estate_offer_rooms':
        try:
            data['rooms'] = int(text)
            if data['rooms'] <= 0:
                raise ValueError
        except ValueError:
            bot.reply_to(message, "Please enter a valid positive number for rooms.")
            return
        
        set_session(tg_id, 'real_estate_offer_address', data)
        bot.reply_to(message, "📍 Enter the address (city and street):")
    
    elif state == 'real_estate_offer_address':
        data['address'] = text
        set_session(tg_id, 'real_estate_offer_description', data)
        bot.reply_to(message, "✍️ Add a description (optional).\n\nSend any text or type /skip to skip.")
    
    elif state == 'real_estate_offer_description':
        if text != '/skip':
            data['description'] = text
        else:
            data['description'] = ""
        
        # Save the offer
        try:
            save_offer(
                tg_id=tg_id,
                text=data.get('description', ''),
                category='real_estate',
                price=data.get('price'),
                property_type=data.get('property_type'),
                property_area=data.get('area'),
                property_address=data.get('address'),
                property_rooms=data.get('rooms')
            )
            
            clear_session(tg_id)
            
            summary = f"""✅ Property listed successfully!

📋 Property Details:
Type: {data.get('property_type', 'N/A')}
Price: {data.get('price', 'Negotiable')}
Area: {data.get('area', 'N/A')} m²
Rooms: {data.get('rooms', 'N/A')}
Address: {data.get('address', 'N/A')}
Description: {data.get('description', '')}"""
            
            bot.reply_to(
                message,
                summary,
                reply_markup=get_main_keyboard(lang)
            )
            
            logger.info(f"Real estate offer created by {tg_id}")
            
        except Exception as e:
            logger.error(f"Error saving real estate offer: {e}")
            bot.reply_to(message, "Error saving your property listing. Please try again.")
    
    # --- REQUEST FLOW ---
    elif state == 'real_estate_request_type':
        property_types = ["Apartment", "House", "Commercial", "Land", "Any"]
        ru_types = ["Квартира", "Дом", "Коммерческая", "Земельный участок", "Любой"]
        
        if lang == 'ru':
            if text not in ru_types:
                bot.reply_to(message, f"Пожалуйста, выберите тип недвижимости из кнопок: {', '.join(ru_types)}")
                return
            type_map = dict(zip(ru_types, property_types))
            data['property_type'] = type_map[text]
        else:
            if text not in property_types:
                bot.reply_to(message, f"Please select property type: {', '.join(property_types)}")
                return
            data['property_type'] = text
        
        set_session(tg_id, 'real_estate_request_price_min', data)
        bot.reply_to(message, "💰 Enter minimum price (in USD) or type '0' for no minimum:")
    
    elif state == 'real_estate_request_price_min':
        try:
            data['price_min'] = int(text) if text != '0' else None
        except ValueError:
            bot.reply_to(message, "Please enter a valid number (e.g., 100000) or '0' for no minimum.")
            return
        
        set_session(tg_id, 'real_estate_request_price_max', data)
        bot.reply_to(message, "💰 Enter maximum price (in USD) or type '0' for no maximum:")
    
    elif state == 'real_estate_request_price_max':
        try:
            data['price_max'] = int(text) if text != '0' else None
        except ValueError:
            bot.reply_to(message, "Please enter a valid number or '0' for no maximum.")
            return
        
        set_session(tg_id, 'real_estate_request_area_min', data)
        bot.reply_to(message, "📐 Enter minimum area (in square meters) or '0' for no minimum:")
    
    elif state == 'real_estate_request_area_min':
        try:
            data['area_min'] = int(text) if text != '0' else None
        except ValueError:
            bot.reply_to(message, "Please enter a valid number or '0' for no minimum.")
            return
        
        set_session(tg_id, 'real_estate_request_area_max', data)
        bot.reply_to(message, "📐 Enter maximum area (in square meters) or '0' for no maximum:")
    
    elif state == 'real_estate_request_area_max':
        try:
            data['area_max'] = int(text) if text != '0' else None
        except ValueError:
            bot.reply_to(message, "Please enter a valid number or '0' for no maximum.")
            return
        
        set_session(tg_id, 'real_estate_request_rooms_min', data)
        bot.reply_to(message, "🛏️ Enter minimum number of rooms or '0' for no minimum:")
    
    elif state == 'real_estate_request_rooms_min':
        try:
            data['rooms_min'] = int(text) if text != '0' else None
        except ValueError:
            bot.reply_to(message, "Please enter a valid number or '0' for no minimum.")
            return
        
        set_session(tg_id, 'real_estate_request_rooms_max', data)
        bot.reply_to(message, "🛏️ Enter maximum number of rooms or '0' for no maximum:")
    
    elif state == 'real_estate_request_rooms_max':
        try:
            data['rooms_max'] = int(text) if text != '0' else None
        except ValueError:
            bot.reply_to(message, "Please enter a valid number or '0' for no maximum.")
            return
        
        set_session(tg_id, 'real_estate_request_address', data)
        bot.reply_to(message, "📍 Enter preferred location (city) or type 'Any' for no preference:")
    
    elif state == 'real_estate_request_address':
        data['address'] = text if text.lower() != 'any' else None
        set_session(tg_id, 'real_estate_request_description', data)
        bot.reply_to(message, "✍️ Add a description of what you're looking for (optional).\n\nSend any text or type /skip to skip.")
    
    elif state == 'real_estate_request_description':
        if text != '/skip':
            data['description'] = text
        else:
            data['description'] = ""
        
        # Save the request
        try:
            save_request(
                tg_id=tg_id,
                text=data.get('description', ''),
                category='real_estate',
                price_min=data.get('price_min'),
                price_max=data.get('price_max'),
                property_type=data.get('property_type'),
                property_area_min=data.get('area_min'),
                property_area_max=data.get('area_max'),
                property_address=data.get('address'),
                property_rooms_min=data.get('rooms_min'),
                property_rooms_max=data.get('rooms_max')
            )
            
            clear_session(tg_id)
            
            summary = f"""✅ Property request created!

📋 Request Details:
Type: {data.get('property_type', 'Any')}
Price: {data.get('price_min', 'Any')} - {data.get('price_max', 'Any')}
Area: {data.get('area_min', 'Any')} - {data.get('area_max', 'Any')} m²
Rooms: {data.get('rooms_min', 'Any')} - {data.get('rooms_max', 'Any')}
Location: {data.get('address', 'Any')}
Description: {data.get('description', '')}"""
            
            bot.reply_to(
                message,
                summary,
                reply_markup=get_main_keyboard(lang)
            )
            
            logger.info(f"Real estate request created by {tg_id}")
            
        except Exception as e:
            logger.error(f"Error saving real estate request: {e}")
            bot.reply_to(message, "Error saving your request. Please try again.")

def cmd_match_property(message: Message):
    """AI-powered matching for real estate offers and requests"""
    if bot is None:
        logger.error("Bot not set in real_estate.py!")
        return
    
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    
    # Send processing message
    status_msg = bot.reply_to(message, "🔍 Searching for matching properties...")
    
    # Find matching offers for this user's requests
    offers = find_matching_offers_for_request(tg_id, limit=5)
    
    if offers:
        # Found offers matching user's request
        text = "🏠 **Matching Properties Found**\n\n"
        for i, offer in enumerate(offers, 1):
            text += f"{i}. {offer.get('property_type', 'Property')} - ${offer.get('price', 'Negotiable')}\n"
            text += f"   Area: {offer.get('area', 'N/A')} m²\n"
            text += f"   Rooms: {offer.get('rooms', 'N/A')}\n"
            text += f"   Location: {offer.get('address', 'N/A')}\n"
            if offer.get('text'):
                text += f"   Details: {offer.get('text', '')[:100]}...\n"
            text += "\n"
        bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            parse_mode='Markdown'
        )
        return
    
    # If no offers found, try to find matching requests for user's offers
    requests = find_matching_requests_for_offer(tg_id, limit=5)
    
    if requests:
        text = "👥 **Buyers Looking for Similar Properties**\n\n"
        for i, req in enumerate(requests, 1):
            text += f"{i}. Looking for {req.get('property_type', 'Property')}\n"
            text += f"   Budget: ${req.get('price_min', 'Any')} - ${req.get('price_max', 'Any')}\n"
            text += f"   Area: {req.get('area_min', 'Any')} - {req.get('area_max', 'Any')} m²\n"
            text += f"   Rooms: {req.get('rooms_min', 'Any')} - {req.get('rooms_max', 'Any')}\n"
            if req.get('text'):
                text += f"   Details: {req.get('text', '')[:100]}...\n"
            text += "\n"
        bot.edit_message_text(
            text,
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            parse_mode='Markdown'
        )
        return
    
    # No matches found
    bot.edit_message_text(
        "No matching properties found. Try:"
        "\n- Creating a property listing with /offer_real_estate"
        "\n- Creating a search request with /request_real_estate"
        "\n- Adjusting your criteria (price, area, rooms, location)",
        chat_id=message.chat.id,
        message_id=status_msg.message_id
    )

# --- COMMAND HANDLERS ---
def cmd_offer_real_estate(message: Message):
    """Start real estate offer flow"""
    if bot is None:
        logger.error("Bot not set in real_estate.py!")
        return
    
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    
    # Show property type selection
    from keyboards import get_property_type_keyboard
    set_session(tg_id, 'real_estate_offer_type', {'language': lang})
    
    if lang == 'ru':
        bot.reply_to(
            message,
            "🏠 Продажа недвижимости\n\nВыберите тип недвижимости:",
            reply_markup=get_property_type_keyboard(lang)
        )
    else:
        bot.reply_to(
            message,
            "🏠 Real Estate Listing\n\nSelect property type:",
            reply_markup=get_property_type_keyboard(lang)
        )

def cmd_request_real_estate(message: Message):
    """Start real estate request flow"""
    if bot is None:
        logger.error("Bot not set in real_estate.py!")
        return
    
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    lang = user.get('language', 'en')
    
    # Show property type selection
    from keyboards import get_property_type_keyboard
    set_session(tg_id, 'real_estate_request_type', {'language': lang})
    
    if lang == 'ru':
        bot.reply_to(
            message,
            "🔍 Поиск недвижимости\n\nВыберите желаемый тип недвижимости:",
            reply_markup=get_property_type_keyboard(lang)
        )
    else:
        bot.reply_to(
            message,
            "🔍 Property Search\n\nSelect desired property type:",
            reply_markup=get_property_type_keyboard(lang)
        )
