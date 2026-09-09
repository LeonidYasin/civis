"""Stage management for coach_bot — handles flow between welcome, reflection, planning, tracking."""

from .prompts import WELCOME_PROMPT, REFLECTION_PROMPT, PLANNING_PROMPT, TRACKING_PROMPT, TRIAL_END_PROMPT
from .model_router import ModelRouter
from .db import CoachDB

class StageRouter:
    def __init__(self):
        self.db = CoachDB()
        self.model = ModelRouter()

    def route(self, user_id: int, text: str, stage: str, status: str) -> str:
        """Route message based on current stage."""
        
        # If free user and not in welcome stage, show paywall
        if status == 'free' and stage != 'welcome' and stage != 'paywall':
            return self._show_paywall()

        if stage == 'welcome':
            return self._handle_welcome(user_id, text)
        elif stage == 'reflection':
            return self._handle_reflection(user_id, text)
        elif stage == 'planning':
            return self._handle_planning(user_id, text)
        elif stage == 'tracking':
            return self._handle_tracking(user_id, text)
        elif stage == 'paywall':
            return self._handle_paywall(user_id, text)
        else:
            return self._handle_welcome(user_id, text)

    def _handle_welcome(self, user_id: int, text: str) -> str:
        """Welcome stage — get to know the user."""
        # Check if user is trying to set a model preference
        if text.lower().startswith("/model"):
            return self._handle_model_change(user_id, text)
        
        # Store user's message
        self.db.save_message(user_id, 'user', text)
        
        # Get history
        history = self.db.get_history(user_id, 6)
        
        # Build context
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        
        # If user has already said something meaningful, move to reflection
        if len(history) > 2:
            self.db.update_user(user_id, stage='reflection')
            prompt = f"{REFLECTION_PROMPT}\n\nИстория диалога:\n{context}\n\nПродолжи диалог."
        else:
            prompt = f"{WELCOME_PROMPT}\n\nПользователь написал: {text}\n\nОтветь."
        
        response = self.model.call(prompt, user_id)
        self.db.save_message(user_id, 'assistant', response)
        return response

    def _handle_reflection(self, user_id: int, text: str) -> str:
        """Reflection stage — deep dive into user's psyche."""
        # Store
        self.db.save_message(user_id, 'user', text)
        
        # Get history
        history = self.db.get_history(user_id, 20)
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        
        # Check if user said something like "I know what I want now"
        keywords = ["знаю что хочу", "понял", "осознал", "теперь я знаю", "моя цель", "я хочу"]
        if any(k in text.lower() for k in keywords):
            self.db.update_user(user_id, stage='planning')
            prompt = f"{PLANNING_PROMPT}\n\nИстория диалога:\n{context}\n\nПользователь сказал, что осознал свою цель. Помоги ему оформить её в план."
        else:
            prompt = f"{REFLECTION_PROMPT}\n\nИстория диалога:\n{context}\n\nПродолжи диалог."
        
        response = self.model.call(prompt, user_id)
        self.db.save_message(user_id, 'assistant', response)
        return response

    def _handle_planning(self, user_id: int, text: str) -> str:
        """Planning stage — turn goals into action plan."""
        self.db.save_message(user_id, 'user', text)
        
        # Check if user provided a goal
        if "цель" in text.lower() or len(text) > 20:
            # Try to extract goal
            goal_text = text
            self.db.add_goal(user_id, goal_text)
        
        history = self.db.get_history(user_id, 20)
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        
        goals = self.db.get_active_goals(user_id)
        goals_text = "\n".join([f"- {g['goal_text']}" for g in goals]) if goals else "пока нет целей"
        
        # If user says they have a plan or ready to start
        keywords = ["план готов", "начать", "готов", "приступаю", "поехали"]
        if any(k in text.lower() for k in keywords):
            self.db.update_user(user_id, stage='tracking')
            prompt = f"{TRACKING_PROMPT}\n\nТвои цели:\n{goals_text}\n\nИстория диалога:\n{context}\n\nПользователь готов начать действовать. Поздравь и поддержи."
        else:
            prompt = f"{PLANNING_PROMPT}\n\nТвои цели:\n{goals_text}\n\nИстория диалога:\n{context}\n\nПомоги пользователю детализировать план действий."
        
        response = self.model.call(prompt, user_id)
        self.db.save_message(user_id, 'assistant', response)
        return response

    def _handle_tracking(self, user_id: int, text: str) -> str:
        """Tracking stage — daily check-ins and motivation."""
        self.db.save_message(user_id, 'user', text)
        
        # Check for /checkin command
        if text.startswith("/checkin"):
            return self._handle_checkin(user_id, text)
        
        history = self.db.get_history(user_id, 20)
        context = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        
        goals = self.db.get_active_goals(user_id)
        goals_text = "\n".join([f"- {g['goal_text']}" for g in goals]) if goals else "пока нет целей"
        
        today_checkin = self.db.get_checkin_today(user_id)
        checkin_status = "ещё не было чекина сегодня" if not today_checkin else f"чекин был: {today_checkin.get('progress', '')}"
        
        prompt = f"{TRACKING_PROMPT}\n\nТвои цели:\n{goals_text}\n\n{checkin_status}\n\nИстория диалога:\n{context}\n\nПродолжи диалог."
        
        response = self.model.call(prompt, user_id)
        self.db.save_message(user_id, 'assistant', response)
        return response

    def _handle_checkin(self, user_id: int, text: str) -> str:
        """Handle /checkin command."""
        parts = text.split(" ", 1)
        if len(parts) < 2:
            return "📋 Напиши /checkin настроение(1-5) прогресс. Например: /checkin 4 сегодня хорошо поработал"
        
        try:
            mood = int(parts[1][0])
            progress = parts[1][1:].strip()
        except:
            return "📋 Формат: /checkin настроение(1-5) прогресс. Например: /checkin 4 сегодня хорошо"
        
        if mood < 1 or mood > 5:
            return "📋 Настроение должно быть от 1 до 5."
        
        self.db.add_checkin(user_id, mood, progress)
        return f"✅ Записал! Настроение: {mood}/5. Прогресс: {progress}.\n\nПродолжай двигаться к цели! 🚀"

    def _handle_model_change(self, user_id: int, text: str) -> str:
        """Handle model preference change."""
        models = {"deepseek", "openai", "claude", "gpt"}
        parts = text.split()
        if len(parts) < 2:
            return "📋 Доступные модели: deepseek, openai, claude.\nНапиши: /model deepseek\n\nИли если хочешь использовать свой ключ: /setkey OPENAI_ключ"
        
        model = parts[1].lower()
        if model in models:
            self.db.update_user(user_id, model_preference=model)
            return f"✅ Модель переключена на {model}."
        else:
            return f"❌ Неизвестная модель. Доступны: deepseek, openai, claude."

    def _show_paywall(self) -> str:
        return TRIAL_END_PROMPT

    def _handle_paywall(self, user_id: int, text: str) -> str:
        """Handle paywall interactions."""
        if "попробовать" in text.lower() or "бесплатно" in text.lower():
            # Start trial
            from datetime import date, timedelta
            start = date.today()
            end = start + timedelta(days=3)
            self.db.update_user(user_id, status='trial', trial_start=start.isoformat(), trial_end=end.isoformat(), stage='reflection')
            return "🎉 Отлично! У тебя 3 дня бесплатного доступа.\n\nДавай продолжим. Расскажи, что тебя сейчас беспокоит или волнует?"
        
        if "купить" in text.lower():
            return "💳 Сейчас мы подключим оплату через ЮKassa.\n\nСсылка для оплаты: [пока заглушка — будет позже]\n\nНапиши 'оплатил', когда завершишь платёж."
        
        if "оплатил" in text.lower():
            self.db.update_user(user_id, status='paid', stage='reflection')
            return "🎉 Спасибо! Ты в программе.\n\nРасскажи, что тебя сейчас беспокоит или волнует?"
        
        return self._show_paywall()
