"""
Coach Bot Handler
Main message handler for Telegram bot
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .db import CoachDB
from .stages import StageRouter
from .model_router import ModelRouter
from .config import config

logger = logging.getLogger(__name__)


class CoachBotHandler:
    """Main handler for coach bot messages"""
    
    def __init__(self):
        self.db = CoachDB()
        self.stage_router = StageRouter()
        self.model_router = ModelRouter()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming message"""
        user_id = update.effective_user.id
        
        # Ignore non-text messages
        if not update.message or not update.message.text:
            return
        
        text = update.message.text.strip()
        
        # Get or create user
        user = self.db.get_or_create_user(user_id)
        stage = user.get('stage', 'welcome')
        status = user.get('status', 'free')
        model_pref = user.get('model_preference', 'deepseek')
        
        # Check if user has reached message limit
        if status == 'free' and stage != 'welcome':
            status_info = self.db.get_user_status(user_id)
            if not status_info.get('can_message', True):
                await self._send_paywall(update)
                return
        
        # Check if user is in payment stage
        if stage == 'payment':
            await self._send_paywall(update)
            return
        
        # Route message
        try:
            response = await self.stage_router.route(
                user_id=user_id,
                message=text,
                stage=stage,
                status=status,
                model_preference=model_pref,
            )
            
            # Send response
            await update.message.reply_text(response)
            
            # Check if user should be moved to reflection after welcome
            if stage == 'welcome':
                new_stage = self.db.get_user(user_id).get('stage', 'welcome')
                if new_stage == 'reflection':
                    await self._send_reflection_trigger(update)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "Извини, произошла ошибка. Попробуй ещё раз или напиши /start"
            )
    
    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start and other commands"""
        user_id = update.effective_user.id
        
        # Get or create user
        user = self.db.get_or_create_user(user_id)
        stage = user.get('stage', 'welcome')
        
        # If user is already past welcome, show status
        if stage != 'welcome':
            status_info = self.db.get_user_status(user_id)
            status_text = f"""👋 Привет! Ты уже в процессе работы.

📊 Твой текущий этап: {stage}
💳 Статус: {status_info['status']}
💬 Осталось сообщений: {status_info.get('messages_left', '∞')}

Просто продолжай диалог, или напиши /reset чтобы начать заново."""
            
            keyboard = [
                [InlineKeyboardButton("📊 Мои цели", callback_data="show_goals")],
                [InlineKeyboardButton("🔑 Сменить модель", callback_data="change_model")],
                [InlineKeyboardButton("💳 Подписка", callback_data="subscription")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(status_text, reply_markup=reply_markup)
            return
        
        # Welcome message for new users
        await self._send_welcome(update)
    
    async def _send_welcome(self, update: Update):
        """Send welcome message"""
        welcome_text = """👋 Привет! Я — бот, который помогает людям разобраться в себе и достигать целей.

Я не даю шаблонных советов. Я задаю вопросы, которые ты себе не задаёшь. И помогаю увидеть то, что ты упускаешь.

Это работает. Вот что говорят люди, которые уже прошли этот путь:

*«Я понял, что 5 лет занимался не тем»*
*«Оказывается, я боялся не неудачи, а успеха»*
*«Я сформулировал цель так, что она перестала быть абстрактной»*

🔥 Первые 3 дня — бесплатно.

Просто расскажи, что тебя беспокоит или что ты хочешь изменить в жизни.

Я слушаю 👂"""
        
        keyboard = [
            [InlineKeyboardButton("💎 Попробовать 3 дня бесплатно", callback_data="start_trial")],
            [InlineKeyboardButton("❓ Что я получу?", callback_data="show_benefits")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def _send_paywall(self, update: Update):
        """Send paywall message"""
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        status = user.get('status', 'free')
        
        # Check if user is on trial
        if status == 'trial':
            trial_end = user.get('trial_end')
            if trial_end:
                days_left = self._days_until(trial_end)
                if days_left > 0:
                    await update.message.reply_text(
                        f"⭐ Ты на пробном периоде. Осталось {days_left} дней.

Ты уже начал путь к изменениям. Продолжай общаться — я здесь, чтобы помочь.

Когда пробный период закончится, ты сможешь оформить подписку."
                    )
                    return
        
        # Full paywall
        keyboard = [
            [InlineKeyboardButton("💎 3 дня бесплатно", callback_data="start_trial")],
            [InlineKeyboardButton("🚀 Подписка 999₽/мес", callback_data="buy_subscription")],
            [InlineKeyboardButton("❓ Что я получу?", callback_data="show_benefits")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            self.stage_router._get_paywall_message(),
            reply_markup=reply_markup,
        )
    
    async def _send_reflection_trigger(self, update: Update):
        """Send trigger when moving to reflection stage"""
        await update.message.reply_text(
            "💡 Интересно... Я начинаю видеть паттерн.

Ты готов перейти на следующий уровень? Мы начнём глубже разбираться в том, что для тебя действительно важно.

Просто продолжай говорить — я буду задавать вопросы."
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "start_trial":
            # Start trial for user
            trial_info = self.db.start_trial(user_id)
            self.db.update_user_stage(user_id, "reflection")
            
            await query.edit_message_text(
                f"✅ Отлично! Ты на пробном периоде до {trial_info['trial_end']}.

Теперь у тебя есть доступ ко всем возможностям.

Расскажи, что тебя беспокоит или что ты хочешь изменить?

Я слушаю 👂"
            )
        
        elif data == "buy_subscription":
            await query.edit_message_text(
                "💳 Подписка — 999 ₽/мес.

Ты получаешь:
✅ Ежедневные чекины
✅ Глубокий анализ целей
✅ Персонализированный план
✅ Поддержка 24/7
✅ Доступ ко всем моделям ИИ

Платёж будет обработан через ЮKassa.

Напиши /pay чтобы оплатить."
            )
        
        elif data == "show_benefits":
            await query.edit_message_text(
                "🌟 Что ты получаешь:

1️⃣ **Глубокое понимание себя** — я помогу тебе увидеть то, что ты упускаешь
2️⃣ **Чёткие цели** — не абстрактные, а реальные, достижимые
3️⃣ **План действий** — разбитый на шаги
4️⃣ **Ежедневная поддержка** — я рядом каждый день
5️⃣ **Прогресс** — ты видишь, как двигаешься

💎 Первые 3 дня — бесплатно.

Нажми «Попробовать 3 дня бесплатно», чтобы начать."
            )
        
        elif data == "show_goals":
            goals = self.db.get_active_goals(user_id)
            if goals:
                text = "🎯 Твои цели:\n\n"
                for i, goal in enumerate(goals, 1):
                    text += f"{i}. {goal['goal_text']}\n"
                await query.edit_message_text(text)
            else:
                await query.edit_message_text(
                    "У тебя пока нет записанных целей. Продолжай диалог, и мы их сформулируем."
                )
        
        elif data == "change_model":
            await self._show_model_selection(query)
        
        elif data == "subscription":
            await self._send_paywall_from_callback(query)
    
    async def _show_model_selection(self, query):
        """Show model selection interface"""
        available = self.model_router.get_available_models()
        
        text = "🔧 Выбери модель ИИ:\n\n"
        
        models_info = {
            "deepseek": "DeepSeek — бесплатно, хороший баланс",
            "openai": "GPT-4 — нужно ввести ключ, высокая точность",
            "claude": "Claude — нужно ввести ключ, лучшая эмпатия",
        }
        
        keyboard = []
        for model in available:
            keyboard.append([InlineKeyboardButton(
                f"✅ {models_info.get(model, model)}",
                callback_data=f"set_model_{model}"
            )])
        
        # Add BYOK option
        keyboard.append([InlineKeyboardButton(
            "🔑 Ввести свой API ключ",
            callback_data="byok"
        )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def _send_paywall_from_callback(self, query):
        """Send paywall from callback"""
        keyboard = [
            [InlineKeyboardButton("💎 3 дня бесплатно", callback_data="start_trial")],
            [InlineKeyboardButton("🚀 Подписка 999₽/мес", callback_data="buy_subscription")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            self.stage_router._get_paywall_message(),
            reply_markup=reply_markup,
        )
    
    @staticmethod
    def _days_until(date_str: str) -> int:
        """Calculate days until a date"""
        from datetime import date
        target = date.fromisoformat(date_str)
        delta = target - date.today()
        return delta.days
