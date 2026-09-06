#!/usr/bin/env python3
"""
Dialog file handlers for Civis bot.
Contains: upload_dialog, my_dialogs, delete_dialog, process_dialogs, handle_document
"""

import logging
import json
import sqlite3
from datetime import datetime

from telebot.types import Message

from database import (
    get_user, get_session, set_session, clear_session,
    save_dialog_file, get_user_dialog_files, get_user_dialog_text,
    mark_dialog_processed, delete_dialog_file, get_dialog_hash, DB_PATH
)
from utils import get_text, get_embedding
from .helpers import log_message, bot

logger = logging.getLogger(__name__)

# --- DIALOG FILE COMMANDS ---

def cmd_upload_dialog(message: Message):
    """Upload a dialog file"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    bot.reply_to(
        message,
        "📄 **Upload your dialog history file**\n\n"
        "Supported formats: `.txt`, `.json`, `.md`\n\n"
        "The file should contain your conversations with AI assistants.\n"
        "This helps create a better embedding profile for matching.\n\n"
        "Just send me a file! 📎",
        parse_mode='Markdown'
    )

def handle_document(message: Message):
    """Handle uploaded document files"""
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    doc = message.document
    filename = doc.file_name
    file_size = doc.file_size
    
    if file_size > 10 * 1024 * 1024:
        bot.reply_to(message, "❌ File too large. Maximum size is 10MB.")
        return
    
    supported_extensions = ['.txt', '.json', '.md']
    ext = filename.lower()
    if not any(ext.endswith(x) for x in supported_extensions):
        bot.reply_to(
            message,
            f"❌ Unsupported file format. Supported: {', '.join(supported_extensions)}"
        )
        return
    
    try:
        file_info = bot.get_file(doc.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8', errors='ignore')
        
        file_type = ext.split('.')[-1]
        file_id = save_dialog_file(tg_id, filename, content, file_type)
        
        bot.reply_to(
            message,
            f"✅ **File uploaded successfully!**\n\n"
            f"📄 {filename}\n"
            f"📊 Size: {file_size} bytes\n"
            f"📝 Type: {file_type}\n\n"
            f"Use `/process_dialogs` to process all uploaded files and update your embedding.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error uploading dialog file: {e}")
        bot.reply_to(message, f"❌ Error uploading file: {e}")

def cmd_my_dialogs(message: Message):
    """List uploaded dialog files"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    files = get_user_dialog_files(tg_id)
    if not files:
        bot.reply_to(
            message,
            "📄 No dialog files uploaded yet.\n\n"
            "Use `/upload_dialog` to upload your conversation history."
        )
        return
    
    text = "📄 **Your Dialog Files**\n\n"
    for file_id, filename, content, file_type, processed in files:
        status = "✅ Processed" if processed else "⏳ Pending"
        text += f"`{file_id}`: {filename} [{file_type}] - {status}\n"
    
    text += "\nUse `/delete_dialog <id>` to remove a file."
    
    bot.reply_to(message, text, parse_mode='Markdown')

def cmd_delete_dialog(message: Message):
    """Delete a dialog file"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /delete_dialog <file_id>\n\nUse /my_dialogs to see your file IDs.")
        return
    
    try:
        file_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Invalid ID. Please provide a number.")
        return
    
    if delete_dialog_file(file_id, tg_id):
        bot.reply_to(message, f"✅ Dialog file #{file_id} deleted successfully.")
    else:
        bot.reply_to(message, f"❌ Dialog file #{file_id} not found or you don't have permission.")

def cmd_process_dialogs(message: Message):
    """Process all dialog files and update embedding"""
    log_message(message, "[CMD]")
    tg_id = message.from_user.id
    user = get_user(tg_id)
    if not user or user.get('status') != 'completed':
        bot.reply_to(message, get_text(tg_id, 'no_profile'))
        return
    
    files = get_user_dialog_files(tg_id, processed=False)
    if not files:
        bot.reply_to(
            message,
            "📄 No pending dialog files to process.\n\n"
            "Upload files with `/upload_dialog` first."
        )
        return
    
    status_msg = bot.reply_to(message, "⏳ Processing dialog files... This may take a moment.")
    
    try:
        all_text = get_user_dialog_text(tg_id)
        
        if not all_text:
            bot.edit_message_text(
                "❌ No dialog content found to process.",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )
            return
        
        openai_key = get_openai_key(tg_id)
        
        # Import get_embedding from utils
        from utils import get_embedding
        embedding = get_embedding(all_text[:8000], openai_key, use_local_fallback=True)
        
        if not embedding:
            bot.edit_message_text(
                "❌ Error generating embedding. Please check your OpenAI key or try again.",
                chat_id=message.chat.id,
                message_id=status_msg.message_id
            )
            return
        
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                tg_id INTEGER PRIMARY KEY,
                embedding TEXT,
                provider TEXT,
                dialog_hash TEXT,
                updated_at TEXT
            )
        """)
        
        import hashlib
        dialog_hash = hashlib.md5(all_text.encode()).hexdigest()
        provider = 'openai' if openai_key else 'local'
        
        cur.execute("""
            INSERT OR REPLACE INTO embeddings (tg_id, embedding, provider, dialog_hash, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (tg_id, json.dumps(embedding), provider, dialog_hash, datetime.now().isoformat()))
        
        for file_id, filename, content, file_type, processed in files:
            mark_dialog_processed(file_id)
        
        conn.commit()
        conn.close()
        
        bot.edit_message_text(
            f"✅ **Dialog files processed successfully!**\n\n"
            f"📄 Processed: {len(files)} files\n"
            f"🧠 Provider: {provider}\n"
            f"📊 Hash: {dialog_hash[:12]}...\n\n"
            f"Your embedding profile has been updated.\n"
            f"Use `/match` to find new matches!",
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error processing dialogs: {e}")
        bot.edit_message_text(
            f"❌ Error processing dialogs: {e}",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )
