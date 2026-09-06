#!/usr/bin/env python3
"""
Минимальная версия бота для проверки соединения с Telegram API.
Используется для диагностики проблем с сетью и прокси.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

# --- НАСТРОЙКА ЛОГГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- ЗАГРУЗКА ПЕРЕМЕННЫХ ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("❌ BOT_TOKEN не найден в .env файле!")
    sys.exit(1)
logger.info("✅ Токен загружен")

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    logger.info(f"📨 Получена команда /start от {message.from_user.id}")
    await message.answer(
        "👋 Привет! Я минимальный тестовый бот Civis.\n"
        "Если ты видишь это сообщение — соединение с Telegram API работает!\n\n"
        "Доступные команды:\n"
        "/ping - проверить соединение\n"
        "/echo <текст> - повторить сообщение\n"
        "/info - информация о боте"
    )

@dp.message(Command("ping"))
async def cmd_ping(message: Message):
    """Проверка соединения"""
    logger.info(f"📨 Получена команда /ping от {message.from_user.id}")
    start_time = datetime.now()
    await message.answer("🏓 Pong!")
    end_time = datetime.now()
    latency = (end_time - start_time).total_seconds() * 1000
    await message.answer(f"⏱️ Задержка: {latency:.0f} мс")

@dp.message(Command("echo"))
async def cmd_echo(message: Message):
    """Повторяет текст пользователя"""
    logger.info(f"📨 Получена команда /echo от {message.from_user.id}")
    text = message.text.replace("/echo", "", 1).strip()
    if text:
        await message.answer(f"🔊 Эхо: {text}")
    else:
        await message.answer("❓ Напиши что-нибудь после /echo")

@dp.message(Command("info"))
async def cmd_info(message: Message):
    """Информация о боте"""
    logger.info(f"📨 Получена команда /info от {message.from_user.id}")
    try:
        me = await bot.me()
        await message.answer(
            f"📊 Информация о боте:\n"
            f"Имя: {me.full_name}\n"
            f"Username: @{me.username}\n"
            f"ID: {me.id}\n"
            f"Токен: {TOKEN[:10]}...{TOKEN[-5:]}"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации о боте: {e}")
        await message.answer(f"❌ Ошибка: {e}")

@dp.message()
async def handle_unknown(message: Message):
    """Обработчик неизвестных сообщений"""
    logger.info(f"📩 Получено неизвестное сообщение от {message.from_user.id}: {message.text}")
    await message.answer(
        "🤔 Я не понимаю эту команду.\n"
        "Используй /start для списка команд."
    )

# --- ЗАПУСК ---
async def main():
    """Главная функция"""
    logger.info("🚀 Запуск минимального бота...")
    
    try:
        # Проверка соединения с Telegram
        logger.info("🔍 Проверка соединения с Telegram API...")
        me = await bot.me()
        logger.info(f"✅ Бот подключен к Telegram API!")
        logger.info(f"📌 Имя бота: {me.full_name}")
        logger.info(f"📌 Username: @{me.username}")
        logger.info(f"📌 ID: {me.id}")
        
        # Запуск polling
        logger.info("🔄 Запуск polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        logger.error(f"📋 Тип ошибки: {type(e).__name__}")
        
        # Подробная диагностика
        logger.error("🔍 Диагностика:")
        logger.error(f"  - Python версия: {sys.version}")
        logger.error(f"  - Токен: {TOKEN[:10]}...{TOKEN[-5:]}")
        
        # Проверка сети
        logger.error("  - Проверка сети...")
        try:
            import socket
            socket.gethostbyname("api.telegram.org")
            logger.error("  ✅ DNS резолвится: api.telegram.org")
        except Exception as dns_err:
            logger.error(f"  ❌ DNS ошибка: {dns_err}")
        
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Необработанная ошибка: {e}")
        sys.exit(1)
