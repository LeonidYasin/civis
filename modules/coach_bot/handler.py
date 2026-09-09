"""
Main handler for Coach Bot
Processes Telegram messages and routes them through stages
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .db import CoachDB
from .stages import StageRouter
from .model_router import ModelRouter
from .payments import PaymentProcessor
from .config import config

logger = logging.getLogger(__name__)


class CoachBotHandler:
    """Main handler for Coach Bot messages"""
    
    def __init__(self):
        self.db = CoachDB()
        self.stage_router = StageRouter()
        self.model_router = ModelRouter()
        self.payment_processor = PaymentProcessor()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        user_id = update.effective_user.id
        text = update.message.text if update.message else None
        
        # Handle callback queries (button clicks)
        if update.callback_query:
            await self._handle_callback(update, context)
            return
        
        if not text:
            await update.message.reply_text("Пожалуйста, напиши сообщение.")
            return
        
        # Get user and status
        user = self.db.get_or_create_user(user_id)
        status_info = self.db.get_user_status(user_id)
        
        # Check if this is a model selection command
        if text.startswith('/model'):
            await self._handle_model_command(update, context)
            return
        
        if text.startswith('/key'):
            await self._handle_key_command(update, context)
            return
        
        if text.startswith('/subscribe'):
            await self._handle_subscribe_command(update, context)
            return
        
        if text.startswith('/status'):
            await self._handle_status_command(update, context)
            return
        
        # Save user message
        self.db.save_message(user_id, 'user', text)
        
        # Route through stages
        stage = user.get('stage', 'welcome')
        status = user.get('status', 'free')
        
        try:
            response, new_stage = await self.stage_router.route(user_id, text, stage, status)
            
            # Update stage if changed
            if new_stage != stage:
                self.db.update_user(user_id, stage=new_stage)
            
            # Save assistant response
            self.db.save_message(user_id, 'assistant', response)
            
            # Send response
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "Извини, произошла ошибка. Попробуй ещё раз или напиши /start для перезапуска."
            )
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == 'start_trial':
            # Activate trial
            end_date = datetime.now().date() + timedelta(days=config.trial_days)
            self.db.update_user(
                user_id,
                status='trial',
                trial_end=end_date.isoformat(),
                stage='reflection'
            )
            await query.edit_message_text(
                f"🎉 Отлично! У тебя есть {config.trial_days} дней бесплатного доступа ко всем функциям.\n\n"
                "Теперь мы можем копнуть глубже. Расскажи, что тебя волнует прямо сейчас?"
            )
            
        elif data == 'buy_subscription':
            # Start payment flow
            payment = self.payment_processor.create_yookassa_payment(
                user_id, 'subscription', config.subscription_price
            )
            if 'error' in payment:
                await query.edit_message_text(
                    "Извини, платёжная система временно недоступна. Попробуй позже."
                )
            else:
                keyboard = [[
                    InlineKeyboardButton(
                        "💳 Перейти к оплате",
                        url=payment['confirmation_url']
                    )
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"💰 Стоимость подписки — {config.subscription_price} ₽/мес.\n\n"
                    "Ты получишь:\n"
                    "✅ Безлимитные диалоги со всеми моделями\n"
                    "✅ Ежедневные чекины и напоминания\n"
                    "✅ Глубокий анализ целей\n"
                    "✅ Приоритетную поддержку\n\n"
                    "Нажми кнопку ниже, чтобы оплатить.",
                    reply_markup=reply_markup
                )
                
        elif data == 'show_benefits':
            await query.edit_message_text(
                "🌟 Что ты получаешь с подпиской:\n\n"
                "🧠 **Все модели ИИ** — DeepSeek, GPT, Claude на выбор\n"
                "💬 **Безлимитные диалоги** — никаких ограничений\n"
                "📅 **Ежедневные чекины** — я буду проверять твой прогресс каждый день\n"
                "🎯 **Глубокий анализ целей** — разбиваем мечты на шаги\n"
                "📊 **Отчёты о прогрессе** — видишь свой рост\n"
                "🔮 **Эмбеддинг-матчинг** — находим людей с похожими целями\n\n"
                "💰 Всего 999 ₽/мес — это цена одного часа с коучем\n"
                "Попробуй 3 дня бесплатно — кнопка выше 👆"
            )
        
        elif data == 'select_model_deepseek':
            self.db.update_user(user_id, model_preference='deepseek')
            await query.edit_message_text(
                "✅ Модель переключена на DeepSeek. Она быстрая и отлично подходит для ежедневных диалогов."
            )
            
        elif data == 'select_model_openai':
            self.db.update_user(user_id, model_preference='openai')
            await query.edit_message_text(
                "✅ Модель переключена на GPT. Она даёт более глубокие и структурированные ответы."
            )
            
        elif data == 'select_model_claude':
            self.db.update_user(user_id, model_preference='claude')
            await query.edit_message_text(
                "✅ Модель переключена на Claude. Она особенно хороша в рефлексии и эмпатии."
            )
    
    async def _handle_model_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /model command"""
        keyboard = [
            [
                InlineKeyboardButton("🧠 DeepSeek", callback_data="select_model_deepseek"),
                InlineKeyboardButton("🤖 GPT", callback_data="select_model_openai"),
            ],
            [
                InlineKeyboardButton("🧬 Claude", callback_data="select_model_claude"),
            ],
            [
                InlineKeyboardButton("🔑 Ввести свой API ключ", callback_data="enter_api_key"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 Выбери модель ИИ, которую я буду использовать:\n\n"
            "**DeepSeek** — быстрая и бесплатная\n"
            "**GPT** — глубокая и структурированная\n"
            "**Claude** — эмпатичная и рефлексивная\n\n"
            "Или введи свой API ключ для любой модели.",
            reply_markup=reply_markup
        )
    
    async def _handle_key_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /key command — set API key"""
        args = context.args
        if not args:
            await update.message.reply_text(
                "🔑 Использование: /key <provider> <api_key>\n\n"
                "Пример: /key openai sk-...\n"
                "Провайдеры: openai, claude, deepseek"
            )
            return
        
        provider = args[0].lower()
        api_key = args[1] if len(args) > 1 else None
        
        if not api_key:
            await update.message.reply_text("❌ Пожалуйста, укажи API ключ.")
            return
        
        # Validate key
        if not self.model_router.validate_api_key(provider, api_key):
            await update.message.reply_text(
                f"❌ Неверный формат ключа для {provider}. Проверь и попробуй снова."
            )
            return
        
        # Save key
        user_id = update.effective_user.id
        self.db.update_user(user_id, api_key=api_key)
        
        # Set model preference
        if provider in ['openai', 'claude', 'deepseek']:
            self.db.update_user(user_id, model_preference=provider)
        
        await update.message.reply_text(
            f"✅ API ключ для {provider} сохранён!\n"
            "Теперь я буду использовать твой ключ для запросов."
        )
    
    async def _handle_subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command"""
        user_id = update.effective_user.id
        status = self.db.get_user_status(user_id)
        
        if status['is_subscribed']:
            days_left = status.get('subscription_days_left', 0)
            await update.message.reply_text(
                f"✅ У тебя уже есть активная подписка. Осталось {days_left} дней."
            )
            return
        
        keyboard = [
            [
                InlineKeyboardButton("💎 Попробовать 3 дня бесплатно", callback_data="start_trial"),
            ],
            [
                InlineKeyboardButton("🚀 Купить подписку — 999 ₽/мес", callback_data="buy_subscription"),
            ],
            [
                InlineKeyboardButton("❓ Что я получу?", callback_data="show_benefits"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌟 **Доступ к полной версии Coach Bot**\n\n"
            "Сейчас у тебя бесплатный доступ. Вот что ты получаешь с подпиской:\n\n"
            "🧠 **Все модели ИИ** — DeepSeek, GPT, Claude\n"
            "💬 **Безлимитные диалоги** — никаких ограничений\n"
            "📅 **Ежедневные чекины** — я проверяю твой прогресс\n"
            "🎯 **Глубокий анализ целей** — разбиваем мечты на шаги\n\n"
            "💳 **999 ₽/мес** или **3 дня бесплатно**\n\n"
            "Выбери свой вариант 👇",
            reply_markup=reply_markup
        )
    
    async def _handle_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        status = self.db.get_user_status(user_id)
        
        model_name = status.get('model_preference', 'deepseek')
        
        message = f"📊 **Твой статус**\n\n"
        message += f"👤 Пользователь: {update.effective_user.username or 'Не указан'}\n"
        message += f"📋 Статус: {status['status']}\n"
        
        if status['is_subscribed']:
            days = status.get('subscription_days_left', 0)
            message += f"💳 Подписка: активна (осталось {days} дней)\n"
        elif status['is_trial_active']:
            days = status.get('trial_days_left', 0)
            message += f"🎁 Триал: активен (осталось {days} дней)\n"
        else:
            message += f"💳 Подписка: не активна\n"
        
        message += f"🤖 Модель: {model_name}\n"
        message += f"💬 Сообщений сегодня: {status['today_messages']} / {status['free_limit']}\n"
        message += f"📌 Этап: {status['stage']}\n"
        
        await update.message.reply_text(message)
