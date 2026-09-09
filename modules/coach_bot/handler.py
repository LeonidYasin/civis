"""Main handler for coach_bot — receives messages and routes to stages."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .db import CoachDB
from .stages import StageRouter

logger = logging.getLogger(__name__)

class CoachBotHandler:
    """Main handler for coach_bot messages."""
    
    def __init__(self):
        self.db = CoachDB()
        self.router = StageRouter()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming message from Telegram."""
        user_id = update.effective_user.id
        text = update.message.text
        
        if not text:
            return
        
        # Get user from DB
        user = self.db.get_or_create_user(user_id)
        stage = user.get('stage', 'welcome')
        status = user.get('status', 'free')
        
        # Log
        logger.info(f"Coach message from {user_id}: stage={stage}, status={status}")
        
        # Handle special commands
        if text.startswith('/'):
            await self._handle_command(update, context, user, text)
            return
        
        # Route through stages
        response = self.router.route(user_id, text, stage, status)
        
        # Save assistant message
        self.db.save_message(user_id, 'assistant', response)
        
        # Send response
        await update.message.reply_text(response)

    async def _handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user: dict, text: str) -> None:
        """Handle slash commands."""
        user_id = update.effective_user.id
        
        if text.startswith('/start'):
            await self._cmd_start(update)
        elif text.startswith('/model'):
            response = self.router.route(user_id, text, user.get('stage', 'welcome'), user.get('status', 'free'))
            await update.message.reply_text(response)
        elif text.startswith('/setkey'):
            await self._cmd_setkey(update, text)
        elif text.startswith('/checkin'):
            response = self.router.route(user_id, text, user.get('stage', 'welcome'), user.get('status', 'free'))
            await update.message.reply_text(response)
        elif text.startswith('/status'):
            await self._cmd_status(update, user)
        elif text.startswith('/help'):
            await self._cmd_help(update)
        else:
            await update.message.reply_text("❓ Неизвестная команда. Напиши /help для списка команд.")

    async def _cmd_start(self, update: Update) -> None:
        """Handle /start command."""
        keyboard = [
            [InlineKeyboardButton("🚀 Начать диалог", callback_data="start_coach")],
            [InlineKeyboardButton("💡 Как это работает?", callback_data="how_it_works")],
            [InlineKeyboardButton("🔑 Ввести свой API ключ", callback_data="set_key")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Привет! Я — твой AI-коуч-помощник.\n\n"
            "Я помогаю людям разобраться в себе, поставить цели и двигаться к ним.\n\n"
            "🎯 Что я умею:\n"
            "• Помогаю понять, чего ты на самом деле хочешь\n"
            "• Помогаю сформулировать цели\n"
            "• Разбиваю цели на шаги\n"
            "• Ежедневно проверяю прогресс\n\n"
            "Выбери действие ниже 👇",
            reply_markup=reply_markup
        )

    async def _cmd_setkey(self, update: Update, text: str) -> None:
        """Handle /setkey command — user sets their own API key."""
        user_id = update.effective_user.id
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2:
            await update.message.reply_text(
                "🔑 Чтобы использовать свой ключ, напиши:\n"
                "/setkey DEEPSEEK_API_КЛЮЧ\n\n"
                "Или для OpenAI:\n"
                "/setkey OPENAI_API_КЛЮЧ\n\n"
                "Или для Claude:\n"
                "/setkey ANTHROPIC_API_КЛЮЧ"
            )
            return
        
        api_key = parts[1].strip()
        
        # Try to validate
        router = ModelRouter()
        if router.validate_key(api_key):
            self.db.update_user(user_id, api_key=api_key)
            await update.message.reply_text("✅ Ключ сохранён и работает!\n\nТеперь ты можешь использовать свой собственный API ключ.")
        else:
            await update.message.reply_text("❌ Не удалось проверить ключ. Убедись, что ключ правильный и попробуй ещё раз.")

    async def _cmd_status(self, update: Update, user: dict) -> None:
        """Handle /status command."""
        user_id = update.effective_user.id
        status = user.get('status', 'free')
        stage = user.get('stage', 'welcome')
        model = user.get('model_preference', 'deepseek')
        has_key = bool(user.get('api_key'))
        
        goals = self.db.get_active_goals(user_id)
        goals_text = "\n".join([f"- {g['goal_text']}" for g in goals]) if goals else "Нет активных целей"
        
        await update.message.reply_text(
            f"📊 **Твой статус**\n\n"
            f"🔹 Статус: {status.upper()}\n"
            f"🔹 Этап: {stage}\n"
            f"🔹 Модель: {model}\n"
            f"🔹 Свой ключ: {'✅ Да' if has_key else '❌ Нет'}\n\n"
            f"🎯 **Цели:**\n{goals_text}\n\n"
            f"📋 Команды: /help — список команд"
        )

    async def _cmd_help(self, update: Update) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "📋 **Список команд**\n\n"
            "/start — начать диалог с коучем\n"
            "/model deepseek|openai|claude — сменить модель\n"
            "/setkey API_KEY — использовать свой ключ\n"
            "/checkin настроение(1-5) прогресс — записать чекин\n"
            "/status — посмотреть свой статус и цели\n"
            "/help — эта помощь\n\n"
            "💡 Просто пиши как человеку — я тебя пойму."
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "start_coach":
            await query.edit_message_text(
                "🔮 Отлично! Расскажи, что тебя сейчас беспокоит или волнует?\n\n"
                "Не надо формулировать цель — просто скажи, что чувствуешь."
            )
        elif data == "how_it_works":
            await query.edit_message_text(
                "💡 **Как это работает**\n\n"
                "1️⃣ **Диалог** — ты просто говоришь, я слушаю и задаю вопросы\n"
                "2️⃣ **Рефлексия** — я помогаю увидеть паттерны и настоящие желания\n"
                "3️⃣ **Планирование** — превращаем осознание в конкретный план\n"
                "4️⃣ **Трекинг** — я проверяю прогресс каждый день\n\n"
                "Всё это — в одном Telegram чате. Никаких анкет и форм.\n\n"
                "Первые 3 дня — бесплатно 🎁"
            )
        elif data == "set_key":
            await query.edit_message_text(
                "🔑 Отлично! Пришли мне свой API ключ командой:\n\n"
                "/setkey ВАШ_КЛЮЧ\n\n"
                "Поддерживаются ключи от: DeepSeek, OpenAI, Anthropic (Claude)."
            )
        else:
            await query.edit_message_text("❓ Неизвестное действие.")

# Need to import ModelRouter here for setkey
from .model_router import ModelRouter
