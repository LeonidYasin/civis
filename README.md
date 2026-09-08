# Civis — Республика профессионалов

**Civis** — это Telegram-бот для поиска и установления связей между людьми на основе их ценностей, целей и профессиональных паттернов. Бот использует AI-матчинг для поиска совместимых людей и позволяет публиковать предложения и запросы (услуги, недвижимость, такси, доставка и т.д.).

---

## 🚀 Установка на свежий VPS (Ubuntu/Debian)

### 1. Подготовка системы

```bash
# Обновление пакетов
sudo apt update && sudo apt upgrade -y

# Установка Python и pip
sudo apt install -y python3 python3-pip python3-venv git

# Установка screen (для запуска в фоне)
sudo apt install -y screen

# Проверка версий
python3 --version
pip3 --version
```

### 2. Клонирование репозитория

```bash
git clone https://github.com/LeonidYasin/civis.git
cd civis/civis_bot
```

### 3. Настройка виртуального окружения

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация
source venv/bin/activate
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

Если `requirements.txt` нет, установи вручную:

```bash
pip install pyTelegramBotAPI requests python-dotenv
```

### 5. Настройка переменных окружения

```bash
# Копирование примера
cp .env.example .env

# Редактирование
nano .env
```

Заполни `.env`:

```env
BOT_TOKEN=ваш_токен_от_BotFather
ADMIN_CHAT_ID=-1001234567890  # ID группы для поддержки (с минусом)
# PROXY_URL=http://127.0.0.1:10809  # Если нужен прокси
```

### 6. Запуск бота

#### Вариант А: Вручную (для теста)

```bash
python bot.py
```

#### Вариант Б: В фоне через screen (рекомендуется)

```bash
# Запуск screen сессии
screen -S civis

# Внутри screen запускаем бота
source venv/bin/activate
python bot.py

# Отключиться от screen: Ctrl+A, затем D
# Подключиться обратно: screen -r civis
```

#### Вариант В: Автозапуск через systemd (для продакшена)

Создай файл `/etc/systemd/system/civis-bot.service`:

```ini
[Unit]
Description=Civis Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/civis/civis_bot
ExecStart=/root/civis/civis_bot/venv/bin/python /root/civis/civis_bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable civis-bot
sudo systemctl start civis-bot
sudo systemctl status civis-bot

# Логи
sudo journalctl -u civis-bot -f
```

---

## 📁 Структура проекта

```
civis/
├── civis_bot/                 # Telegram-бот
│   ├── bot.py                 # Точка входа
│   ├── config.py              # Конфигурация
│   ├── database.py            # Работа с SQLite
│   ├── handlers/              # Обработчики команд
│   │   ├── core.py            # Основные команды
│   │   ├── marketplace.py     # Предложения и запросы
│   │   ├── dialogs.py         # Загрузка диалогов
│   │   ├── subscription.py    # Подписки и AI-матчинг
│   │   └── ...
│   ├── keyboards.py           # Клавиатуры
│   ├── locales.py             # Переводы (EN/RU)
│   ├── utils.py               # Вспомогательные функции
│   ├── requirements.txt
│   └── .env.example
├── docs/                      # Лендинг (GitHub Pages)
└── README.md
```

---

## 🤖 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Создать или просмотреть профиль |
| `/menu` | Показать главное меню |
| `/profile` | Просмотреть профиль |
| `/embedding` | Просмотреть AI-эмбеддинг профиля |
| `/citizens` | Список всех граждан |
| `/search` | Поиск граждан |
| `/offer` | Опубликовать предложение |
| `/request` | Опубликовать запрос |
| `/offer_real_estate` | Быстрое предложение недвижимости |
| `/offer_taxi` | Быстрое предложение такси |
| `/offer_delivery` | Быстрое предложение доставки |
| `/my_offers` | Мои предложения |
| `/my_requests` | Мои запросы |
| `/delete_offer` | Удалить предложение по ID |
| `/delete_request` | Удалить запрос по ID |
| `/marketplace` | Просмотр маркетплейса |
| `/subscribe` | Тарифы |
| `/match` | AI-матчинг |
| `/setkey` | Установить OpenAI API ключ |
| `/upload_dialog` | Загрузить историю диалогов |
| `/my_dialogs` | Список загруженных диалогов |
| `/process_dialogs` | Обработать диалоги |
| `/language` | Сменить язык |
| `/support` | Связаться с разработчиком |
| `/status` | Статус бота |
| `/help` | Помощь |
| `/cancel` | Отменить текущую операцию |
| `/done` | Завершить выбор ценностей |

---

## 🧠 AI-матчинг

Civis использует OpenAI эмбеддинги или локальную модель `all-MiniLM-L6-v2` для поиска совместимых людей. Для работы нужно:

1. Установить OpenAI API ключ через `/setkey` (опционально, если используешь OpenAI)
2. Для локальной модели установить `sentence-transformers`:
   ```bash
   pip install sentence-transformers
   ```

---

## 📊 База данных

Бот использует SQLite (`civis_data.db`). Основные таблицы:

| Таблица | Назначение |
|---------|------------|
| `users` | Профили граждан |
| `offers` | Предложения (маркетплейс) |
| `requests` | Запросы (маркетплейс) |
| `subscriptions` | Подписки и лимиты |
| `dialog_files` | Загруженные истории диалогов |
| `embeddings` | Кэш AI-эмбеддингов |
| `sessions` | Временные состояния |

---

## 🐛 Устранение проблем

### Ошибка: `pip not found`
```bash
sudo apt install python3-pip
```

### Ошибка: `ModuleNotFoundError`
Убедись, что виртуальное окружение активировано:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Ошибка подключения к Telegram API
Если Telegram заблокирован, используй прокси в `.env`:
```
PROXY_URL=http://127.0.0.1:10809
```

### Бот не отвечает
Проверь логи:
```bash
journalctl -u civis-bot -f
```

---

## 📄 Лицензия

MIT © Leonid Yasin

---

## 📬 Контакты

- **Telegram-бот:** [@civis_matcher_bot](https://t.me/civis_matcher_bot)
- **GitHub:** [LeonidYasin/civis](https://github.com/LeonidYasin/civis)
- **Поддержка:** `/support` в боте
