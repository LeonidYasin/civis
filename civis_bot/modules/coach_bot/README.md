# Coach Bot Module

AI-коуч для постановки целей и саморазвития в Telegram.

## Основные возможности

- **Бесплатный вход** — первые 3 дня бесплатно
- **Подписка** — полный доступ к функциям
- **BYOK (Bring Your Own Key)** — пользователь может использовать свой API ключ
- **Выбор модели** — DeepSeek (по умолчанию), OpenAI GPT, Claude
- **Ежедневные чекины** — отслеживание прогресса
- **Трекинг целей** — постановка и контроль целей
- **Рефлексия** — глубокий анализ мыслей и желаний

## Архитектура модуля

```
coach_bot/
├── __init__.py          # Экспорт основных компонентов
├── handler.py           # Основной обработчик сообщений
├── models.py            # Модели базы данных
├── stages.py            # Логика этапов (welcome → reflection → planning → tracking)
├── prompts.py           # Системные промпты для каждого этапа
└── model_router.py      # Маршрутизация запросов к моделям
```

## Этапы работы

1. **Welcome** — знакомство, создание безопасной атмосферы
2. **Reflection** — глубокая рефлексия, поиск истинных желаний
3. **Planning** — постановка целей и планирование
4. **Tracking** — ежедневный трекинг и поддержка

## Модели и цены

| Модель | Цена за 1K токенов (input/output) |
|--------|-----------------------------------|
| DeepSeek | $0.00014 / $0.00028 |
| OpenAI GPT | $0.003 / $0.006 |
| Claude | $0.003 / $0.015 |
| Custom (BYOK) | по вашему тарифу |

## Использование

```python
from modules.coach_bot import CoachBotHandler

# Инициализация с фабрикой сессий БД
handler = CoachBotHandler(session_factory)

# Обработка сообщения
await handler.handle_message(update, context)

# Обработка callback-запросов
await handler.handle_callback(update, context)
```

## Платежи

Модуль поддерживает два способа оплаты:
- **ЮKassa** — для российских пользователей
- **Stripe** — для международных

Планы:
- **Monthly** — 999 ₽/мес
- **Premium** — 2 999 ₽/мес (приоритетный матчинг + эмбеддинги)

## Переменные окружения

```env
# API ключи (опционально, если используется BYOK)
DEEPSEEK_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# Платежи
YUKASSA_SHOP_ID=your_shop_id
YUKASSA_SECRET_KEY=your_secret
STRIPE_SECRET_KEY=your_stripe_key
```

## Лицензия

MIT
