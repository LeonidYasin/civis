# CIVIS — Республика профессионалов

CIVIS — это открытая система матчинга людей по их реальным паттернам поведения, ценностям и целям.

## 📁 Структура репозитория

```
civis/
├── civis_app/          # Flutter-приложение (iOS + Android)
│   ├── lib/            # Исходный код
│   ├── pubspec.yaml    # Зависимости
│   └── .env.example    # Пример переменных окружения
├── civis_bot/          # Telegram-бот (Python)
│   ├── bot.py          # Основной код
│   ├── requirements.txt # Зависимости Python
│   └── .env.example    # Пример переменных окружения
└── .github/            # GitHub Actions workflows
    ├── build_android.yml # Сборка APK
    └── build_ios.yml     # Сборка IPA
```

## 🚀 Запуск Flutter-приложения

```bash
cd civis_app
flutter pub get
flutter run
```

## 🤖 Запуск Telegram-бота

### Linux / Mac
```bash
cd civis_bot
chmod +x run_bot.sh
./run_bot.sh
```

### Windows
```cmd
cd civis_bot
run_bot.bat
```

## 🔧 Настройка

1. Скопируй `.env.example` в `.env`
2. Заполни переменные:
   - `BOT_TOKEN` — токен от @BotFather
   - `API_URL` — URL твоего сервера для отправки заявок

## 📦 Сборка через GitHub Actions

- Android APK: после push в main скачивай из Artifacts
- iOS IPA: требуется macOS runner

## 📱 Установка на телефон

1. Скачай APK из Artifacts
2. Разреши установку из неизвестных источников
3. Установи и запусти

## 🧠 Архитектура

- **Flutter** — кроссплатформенный клиент
- **SQLite** — локальное хранение профилей
- **Dio** — HTTP-клиент для отправки данных на сервер
- **aiogram** — Telegram-бот на Python

## 📄 Лицензия

MIT
