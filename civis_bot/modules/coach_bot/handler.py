"""Основной обработчик coach_bot"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
from sqlalchemy.orm import sessionmaker

from .models import CoachUser, CoachMessage, CoachGoal, CoachInsight
from .stages import StageRouter
from .prompts import SYSTEM_PROMPTS
from .model_router import ModelRouter

logger = logging.getLogger(__name__)

class CoachBotHandler:
    """Обработчик коуч-бота"""
    
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory
        self.stage_router = StageRouter()
        self.model_router = ModelRouter()
    
    def get_user(self, user_id: int) -> CoachUser:
        """Получить или создать пользователя"""
        session = self.session_factory()
        try:
            user = session.query(CoachUser).filter_by(user_id=user_id).first()
            if not user:
                user = CoachUser(user_id=user_id)
                session.add(user)
                session.commit()
            return user
        finally:
            session.close()
    
    def update_user(self, user_id: int, **kwargs):
        """Обновить данные пользователя"""
        session = self.session_factory()
        try:
            user = session.query(CoachUser).filter_by(user_id=user_id).first()
            if user:
                for key, value in kwargs.items():
                    setattr(user, key, value)
                session.commit()
        finally:
            session.close()
    
    def save_message(self, user_id: int, role: str, content: str, model: str = None):
        """Сохранить сообщение в историю"""
        session = self.session_factory()
        try:
            msg = CoachMessage(user_id=user_id, role=role, content=content, model=model)
            session.add(msg)
            
            # Обновляем счётчик сообщений
            user = session.query(CoachUser).filter_by(user_id=user_id).first()
            if user:
                user.messages_count += 1
                user.last_message_date = datetime.utcnow().date()
            
            session.commit()
        finally:
            session.close()
    
    def get_history(self, user_id: int, limit: int = 20) -> list:
        """Получить историю диалога"""
        session = self.session_factory()
        try:
            messages = session.query(CoachMessage).filter_by(user_id=user_id).order_by(
                CoachMessage.created_at.desc()
            ).limit(limit).all()
            return [{"role": m.role, "content": m.content} for m in reversed(messages)]
        finally:
            session.close()
    
    def get_goals(self, user_id: int) -> list:
        """Получить активные цели пользователя"""
        session = self.session_factory()
        try:
            goals = session.query(CoachGoal).filter_by(
                user_id=user_id, status='active'
            ).order_by(CoachGoal.priority).all()
            return [{"id": g.id, "text": g.goal_text, "progress": g.progress} for g in goals]
        finally:
            session.close()
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка входящего сообщения"""
        user_id = update.effective_user.id
        text = update.message.text
        
        # Получаем пользователя
        user = self.get_user(user_id)
        
        # Проверяем лимиты для бесплатных пользователей
        if user.status == 'free' and user.messages_count >= 5:
            await self._show_paywall(update, user)
            return
        
        # Проверяем статус подписки
        if user.status in ['trial', 'paid', 'premium']:
            if user.subscription_end and user.subscription_end < datetime.utcnow():
                self.update_user(user_id, status='free')
                await self._show_expired(update)
                return
        
        # Определяем этап
        stage = user.stage
        
        # Получаем историю для контекста
        history = self.get_history(user_id)
        goals = self.get_goals(user_id)
        
        # Выбираем модель
        model = user.preferred_model or 'deepseek'
        
        # Генерируем ответ через stage_router
        response = await self.stage_router.route(
            user_id=user_id,
            text=text,
            stage=stage,
            history=history,
            goals=goals,
            model=model
        )
        
        # Сохраняем сообщения
        self.save_message(user_id, 'user', text, model)
        self.save_message(user_id, 'assistant', response['content'], model)
        
        # Обновляем статус если нужно
        if response.get('new_stage'):
            self.update_user(user_id, stage=response['new_stage'])
        
        # Отправляем ответ
        reply_markup = None
        if response.get('keyboard'):
            reply_markup = InlineKeyboardMarkup(response['keyboard'])
        
        await update.message.reply_text(response['content'], reply_markup=reply_markup)
    
    async def _show_paywall(self, update: Update, user: CoachUser):
        """Показать платную стену"""
        keyboard = [
            [InlineKeyboardButton("💎 Попробовать 3 дня бесплатно", callback_data="coach_trial")],
            [InlineKeyboardButton("🚀 Подписка — 999 ₽/мес", callback_data="coach_pay_monthly")],
            [InlineKeyboardButton("📊 Премиум — 2 999 ₽/мес", callback_data="coach_pay_premium")],
            [InlineKeyboardButton("🔑 Ввести свой API ключ", callback_data="coach_byok")],
            [InlineKeyboardButton("❓ Что я получу?", callback_data="coach_benefits")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔥 Ты уже использовал 5 бесплатных сообщений. Теперь — самое интересное.\n\n"
            "✅ Ежедневные чекины\n"
            "✅ Глубокий анализ твоих целей\n"
            "✅ План действий на месяц\n"
            "✅ Поддержка 24/7\n"
            "✅ Доступ ко всем моделям\n\n"
            "Выбери вариант:",
            reply_markup=reply_markup
        )
    
    async def _show_expired(self, update: Update):
        """Показать, что подписка истекла"""
        keyboard = [
            [InlineKeyboardButton("🔄 Возобновить подписку", callback_data="coach_renew")],
            [InlineKeyboardButton("💎 Попробовать 3 дня", callback_data="coach_trial")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⏰ Твоя подписка истекла. Но ты можешь продолжить — мы готовы помочь тебе снова.",
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback-запросов"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        data = query.data
        
        if data == "coach_trial":
            # Начинаем пробный период
            self.update_user(
                user_id,
                status='trial',
                trial_start=datetime.utcnow(),
                trial_end=datetime.utcnow() + timedelta(days=3),
                stage='reflection'
            )
            await query.edit_message_text(
                "🎉 Поздравляю! У тебя 3 дня бесплатного доступа.\n\n"
                "Расскажи, что тебя беспокоит прямо сейчас? Не надо формулировать цель — просто скажи, что чувствуешь."
            )
        
        elif data == "coach_pay_monthly":
            await query.edit_message_text(
                "💰 Оплата 999 ₽/мес\n\n"
                "Сейчас я перенаправлю тебя на страницу оплаты.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Оплатить через ЮKassa", url="https://example.com/pay")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="coach_back")],
                ])
            )
        
        elif data == "coach_pay_premium":
            await query.edit_message_text(
                "💰 Оплата 2 999 ₽/мес — Премиум\n\n"
                "Дополнительно:\n"
                "✅ Приоритетный матчинг\n"
                "✅ Полный доступ к эмбеддингам\n"
                "✅ Персональная аналитика\n"
                "✅ Приоритетная поддержка\n\n"
                "Перехожу к оплате...",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💳 Оплатить через ЮKassa", url="https://example.com/pay-premium")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="coach_back")],
                ])
            )
        
        elif data == "coach_byok":
            await query.edit_message_text(
                "🔑 Введи свой API ключ.\n\n"
                "Формат:\n"
                "`sk-...` — для OpenAI\n"
                "`claude-...` — для Claude\n"
                "`ds-...` — для DeepSeek\n\n"
                "Напиши ключ в следующем сообщении.\n"
                "(Я сохраню его в зашифрованном виде)"
            )
            # Устанавливаем состояние ожидания ключа
            context.user_data['awaiting_api_key'] = True
        
        elif data == "coach_benefits":
            await query.edit_message_text(
                "✨ Что ты получаешь с подпиской:\n\n"
                "🧠 **Глубокая рефлексия** — я задаю вопросы, которые ты себе не задаёшь\n"
                "🎯 **Чёткие цели** — помогаю сформулировать и разбить на шаги\n"
                "📅 **Ежедневный трекинг** — не даю сбиться с пути\n"
                "🔄 **Доступ ко всем моделям** — DeepSeek, GPT, Claude\n"
                "💡 **Инсайты** — вижу паттерны, которые ты упускаешь\n\n"
                "Попробуй 3 дня бесплатно — и реши сам.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Попробовать", callback_data="coach_trial")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="coach_back")],
                ])
            )
        
        elif data == "coach_back":
            await self._show_paywall(update, self.get_user(user_id))
        
        elif data == "coach_renew":
            await query.edit_message_text(
                "🔄 Возобновление подписки\n\n"
                "Выбери план:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 999 ₽/мес", callback_data="coach_pay_monthly")],
                    [InlineKeyboardButton("📊 2 999 ₽/мес — Премиум", callback_data="coach_pay_premium")],
                ])
            )
    
    async def handle_api_key_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ввода API ключа"""
        user_id = update.effective_user.id
        key = update.message.text.strip()
        
        # Определяем провайдера по формату ключа
        provider = 'custom'
        if key.startswith('sk-'):
            provider = 'openai'
        elif key.startswith('claude-'):
            provider = 'claude'
        elif key.startswith('ds-'):
            provider = 'deepseek'
        
        # Сохраняем ключ (в реальном проекте нужно шифровать)
        self.update_user(user_id, api_key=key, api_key_provider=provider)
        
        await update.message.reply_text(
            f"✅ Ключ сохранён! Теперь я буду использовать {provider} для ответов.\n\n"
            "Можешь продолжать диалог."
        )
        
        context.user_data['awaiting_api_key'] = False
