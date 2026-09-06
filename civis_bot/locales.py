#!/usr/bin/env python3
"""
Localization file for Civis bot.
Contains all texts in English and Russian.
"""

TEXTS = {
    'en': {
        'welcome': "Welcome to Civis!\n\nCivis is a Republic of Professionals - a community where people connect based on trust, values, and shared goals.\n\nWe use AI to understand who you are and match you with the right people, projects, and opportunities.\n\nNo resumes. No cold calls. Just real connections.\n\nLet's create your profile!",
        'language_set': "Language set to English.",
        'choose_language': "Choose your language:",
        'language_changed': "Language changed to English.",
        'name_ask': "What is your name?",
        'about_ask': "Tell me a bit about yourself and your professional goals.\n(Just a few sentences is fine.)",
        'about_short': "That's a bit short. Could you tell me a little more about yourself?",
        'values_intro': "To match you with the right people, we need to understand what matters to you in work.\n\nSelect 3 key values from the list below.\n(Just click the buttons one by one. You'll see your selection below.)",
        'values_ask': "Choose 3 values from the buttons below:",
        'values_selected': "Selected: {values}\n\nChoose {remaining} more or click /done when finished:",
        'values_error': "Please select 3 values total. You have {count}. Choose {remaining} more.",
        'values_complete': "Great! You've selected 3 values.",
        'role_ask': "What is your main role?",
        'role_error': "Please select a role from the buttons.",
        'format_ask': "Which communication format is convenient for you?",
        'format_error': "Please select a format from the buttons.",
        'profile_complete': "Congratulations! You are now a citizen of Civis!",
        'welcome_citizen': "Welcome to Civis, {name}!\n\nYou are now a citizen. You can:\n/offer - Publish an offer\n/request - Publish a request\n/marketplace - View marketplace\n/language - Change language\n/profile - View your profile\n/survey - Update your profile\n/subscribe - View subscription plans\n/match - AI-powered matching",
        'cancel': "Cancelled.",
        'unknown': "Use /start to create your profile or /help for commands.",
        'profile': "Profile:",
        'no_profile': "You don't have a profile yet. Use /start to create one!",
        'help': "Civis Bot\n\n/start - Create your profile\n/profile - View your profile\n/survey - Update your profile\n/offer - Publish an offer\n/request - Publish a request\n/marketplace - View marketplace\n/language - Change language\n/subscribe - View subscription plans\n/match - AI-powered matching\n/status - Bot status\n/cancel - Cancel current operation\n/help - Show this message",
        'status': "Civis Bot\n\nProfiles: {count}\nProxy: {proxy}",
        'done_button': "/done",
        'marketplace_empty': "Marketplace is empty. Use /offer or /request to publish something.",
        'offer_prompt': "Describe what you are offering (service, product, knowledge, etc.):",
        'request_prompt': "Describe what you are looking for (service, product, etc.):",
        'offer_saved': "Your offer has been published!",
        'request_saved': "Your request has been published!",
        'language_instruction': "Send /language to change language at any time.",
        'subscribe_title': "💳 Subscription Plans",
        'subscribe_current': "Current plan: {plan}",
        'subscribe_remaining': "Matches remaining: {remaining}",
        'subscribe_free': "📌 Free — $0/month\n  • 3 matches/month\n  • Basic profile\n  • View citizens",
        'subscribe_premium': "⭐ Premium — $9.99/month\n  • Unlimited matches\n  • Priority in search\n  • Export profile (JSON)\n  • Early access to new features",
        'subscribe_lifetime': "🚀 Lifetime — $99 one-time\n  • All Premium features\n  • MCP tools access\n  • Lifetime updates",
        'subscribe_upgrade': "To upgrade, send /setkey to use your own OpenAI key, or contact @civis_support for payment.",
        'setkey_prompt': "Please provide your OpenAI API key:\n`/setkey sk-...`\n\nYou can get your key at: https://platform.openai.com/api-keys",
        'setkey_invalid': "❌ Invalid OpenAI key format. It should start with 'sk-'. Please check and try again.",
        'setkey_saved': "✅ OpenAI key saved successfully! You can now use /match for AI-powered matching.",
        'setkey_required': "❌ You need to set your OpenAI API key first.\nUse `/setkey sk-...` to set your key.",
        'match_no_citizens': "No citizens to match with yet. Come back later!",
        'match_no_others': "No other citizens to match with yet. Share the bot with friends!",
        'match_in_progress': "🔍 AI Matching in progress...\n\nYour profile:\n{profile}\n\nWe're analyzing {count} other citizens.\nFull AI matching coming soon!",
        'match_limit_exceeded': "❌ You've used all your free matches.\nRemaining: {remaining}\nUse `/subscribe` to upgrade to Premium.",
        'values_list': "Honesty, Expertise, Initiative, Reliability, Speed, Empathy, Systematic, Creativity, Openness, Ambition",
        'buttons': {
            'offer': "/offer",
            'request': "/request",
            'marketplace': "/marketplace",
            'profile': "/profile",
            'help': "/help",
        }
    },
    'ru': {
        'welcome': "Добро пожаловать в Civis!\n\nCivis — это Республика Профессионалов — сообщество, где люди соединяются на основе доверия, ценностей и общих целей.\n\nМы используем ИИ, чтобы понять, кто вы, и подобрать вам подходящих людей, проекты и возможности.\n\nБез резюме. Без холодных звонков. Только настоящие связи.\n\nДавайте создадим ваш профиль!",
        'language_set': "Язык установлен: Русский.",
        'choose_language': "Выберите язык:",
        'language_changed': "Язык изменён на Русский.",
        'name_ask': "Как вас зовут?",
        'about_ask': "Расскажите немного о себе и своих профессиональных целях.\n(Достаточно пары предложений.)",
        'about_short': "Это коротковато. Не могли бы вы рассказать о себе чуть больше?",
        'values_intro': "Чтобы подобрать вам подходящих людей, нам нужно понять, что для вас важно в работе.\n\nВыберите 3 ключевые ценности из списка ниже.\n(Нажимайте кнопки по одной. Ваш выбор будет отображаться ниже.)",
        'values_ask': "Выберите 3 ценности из кнопок ниже:",
        'values_selected': "Выбрано: {values}\n\nВыберите ещё {remaining} или нажмите /done когда закончите:",
        'values_error': "Пожалуйста, выберите 3 ценности. Вы выбрали {count}. Осталось {remaining}.",
        'values_complete': "Отлично! Вы выбрали 3 ценности.",
        'role_ask': "Какова ваша основная роль?",
        'role_error': "Пожалуйста, выберите роль из кнопок.",
        'format_ask': "Какой формат общения вам удобен?",
        'format_error': "Пожалуйста, выберите формат из кнопок.",
        'profile_complete': "Поздравляем! Теперь вы гражданин Civis!",
        'welcome_citizen': "Добро пожаловать в Civis, {name}!\n\nТеперь вы гражданин. Вы можете:\n/offer - Опубликовать предложение\n/request - Опубликовать запрос\n/marketplace - Посмотреть маркетплейс\n/language - Сменить язык\n/profile - Посмотреть профиль\n/survey - Обновить профиль\n/subscribe - Посмотреть тарифы\n/match - ИИ-матчинг",
        'cancel': "Отменено.",
        'unknown': "Используйте /start для создания профиля или /help для помощи.",
        'profile': "Профиль:",
        'no_profile': "У вас ещё нет профиля. Используйте /start, чтобы создать его!",
        'help': "Civis Бот\n\n/start - Создать профиль\n/profile - Мой профиль\n/survey - Обновить профиль\n/offer - Опубликовать предложение\n/request - Опубликовать запрос\n/marketplace - Посмотреть маркетплейс\n/language - Сменить язык\n/subscribe - Посмотреть тарифы\n/match - ИИ-матчинг\n/status - Статус бота\n/cancel - Отменить текущую операцию\n/help - Помощь",
        'status': "Civis Бот\n\nПрофилей: {count}\nПрокси: {proxy}",
        'done_button': "/done",
        'marketplace_empty': "Маркетплейс пуст. Используйте /offer или /request, чтобы что-то опубликовать.",
        'offer_prompt': "Опишите, что вы предлагаете (услуга, товар, знания и т.д.):",
        'request_prompt': "Опишите, что вы ищете (услуга, товар и т.д.):",
        'offer_saved': "Ваше предложение опубликовано!",
        'request_saved': "Ваш запрос опубликован!",
        'language_instruction': "Отправьте /language, чтобы сменить язык в любой момент.",
        'subscribe_title': "💳 Тарифы",
        'subscribe_current': "Текущий тариф: {plan}",
        'subscribe_remaining': "Осталось матчей: {remaining}",
        'subscribe_free': "📌 Бесплатный — $0/мес\n  • 3 матча в месяц\n  • Базовый профиль\n  • Просмотр граждан",
        'subscribe_premium': "⭐ Премиум — $9.99/мес\n  • Безлимитные матчи\n  • Приоритет в поиске\n  • Экспорт профиля (JSON)\n  • Ранний доступ к новым функциям",
        'subscribe_lifetime': "🚀 Навсегда — $99 разово\n  • Все функции Премиум\n  • Доступ к MCP-инструментам\n  • Пожизненные обновления",
        'subscribe_upgrade': "Чтобы перейти на платный тариф, отправьте /setkey со своим OpenAI ключом, или напишите @civis_support для оплаты.",
        'setkey_prompt': "Пожалуйста, введите ваш OpenAI API ключ:\n`/setkey sk-...`\n\nПолучить ключ можно здесь: https://platform.openai.com/api-keys",
        'setkey_invalid': "❌ Неверный формат OpenAI ключа. Он должен начинаться с 'sk-'. Пожалуйста, проверьте и попробуйте снова.",
        'setkey_saved': "✅ OpenAI ключ сохранён! Теперь вы можете использовать /match для ИИ-матчинга.",
        'setkey_required': "❌ Вам нужно сначала установить OpenAI API ключ.\nИспользуйте `/setkey sk-...` чтобы установить ключ.",
        'match_no_citizens': "Нет граждан для матчинга. Зайдите позже!",
        'match_no_others': "Нет других граждан для матчинга. Поделитесь ботом с друзьями!",
        'match_in_progress': "🔍 ИИ-матчинг в процессе...\n\nВаш профиль:\n{profile}\n\nАнализируем {count} других граждан.\nПолный ИИ-матчинг скоро будет доступен!",
        'match_limit_exceeded': "❌ Вы использовали все бесплатные матчи.\nОсталось: {remaining}\nИспользуйте `/subscribe` чтобы перейти на Премиум.",
        'values_list': "Честность, Экспертиза, Инициатива, Надёжность, Скорость, Эмпатия, Системность, Креативность, Открытость, Амбициозность",
        'buttons': {
            'offer': "/offer",
            'request': "/request",
            'marketplace': "/marketplace",
            'profile': "/profile",
            'help': "/help",
        }
    }
}

# Value mappings for both languages
VALUE_MAP = {
    'en': {
        'Honesty': 'Honesty',
        'Expertise': 'Expertise',
        'Initiative': 'Initiative',
        'Reliability': 'Reliability',
        'Speed': 'Speed',
        'Empathy': 'Empathy',
        'Systematic': 'Systematic',
        'Creativity': 'Creativity',
        'Openness': 'Openness',
        'Ambition': 'Ambition',
    },
    'ru': {
        'Честность': 'Honesty',
        'Экспертиза': 'Expertise',
        'Инициатива': 'Initiative',
        'Надёжность': 'Reliability',
        'Скорость': 'Speed',
        'Эмпатия': 'Empathy',
        'Системность': 'Systematic',
        'Креативность': 'Creativity',
        'Открытость': 'Openness',
        'Амбициозность': 'Ambition',
    }
}

def get_value_buttons(lang):
    """Get value buttons for the given language"""
    if lang == 'ru':
        return ["Честность", "Экспертиза", "Инициатива", "Надёжность", "Скорость", "Эмпатия", "Системность", "Креативность", "Открытость", "Амбициозность"]
    return ["Honesty", "Expertise", "Initiative", "Reliability", "Speed", "Empathy", "Systematic", "Creativity", "Openness", "Ambition"]

def get_roles(lang):
    """Get roles for the given language"""
    if lang == 'ru':
        return ["Исполнитель", "Заказчик", "Координатор", "Инвестор", "Продавец", "Покупатель"]
    return ["Executor", "Customer", "Coordinator", "Investor", "Seller", "Buyer"]

def get_formats(lang):
    """Get formats for the given language"""
    if lang == 'ru':
        return ["Текст", "Голос", "Видео", "Любой"]
    return ["Text", "Voice", "Video", "Any"]
