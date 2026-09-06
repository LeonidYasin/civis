#!/usr/bin/env python3
"""
Основной бот Civis с поддержкой прокси через переменные окружения.
Автоматически использует HTTP_PROXY/HTTPS_PROXY если они заданы.
"""

import asyncio
import logging
import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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

# --- ПРОВЕРКА ПРОКСИ ---
http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
if http_proxy or https_proxy:
    logger.info(f"🔌 Используется прокси: {https_proxy or http_proxy}")
else:
    logger.info("🔌 Прокси не настроен")

# --- ПОДКЛЮЧЕНИЕ К БАЗЕ (SQLite) ---
DB_PATH = Path(__file__).parent / "civis_data.db"

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_user_id TEXT,
                tg_username TEXT,
                text TEXT,
                selected_values TEXT,
                role TEXT,
                format TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return False

def save_profile(tg_user_id, tg_username, text, values, role, format):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO profiles (tg_user_id, tg_username, text, selected_values, role, format, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tg_user_id, tg_username, text, values, role, format, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")
        return False

# --- ИНИЦИАЛИЗАЦИЯ ---
if not init_db():
    sys.exit(1)

# --- СОСТОЯНИЯ АНКЕТЫ ---
class Form(StatesGroup):
    text = State()
    values = State()
    role = State()
    format = State()

# --- КНОПКИ ---
values_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Честность"), KeyboardButton(text="Экспертиза")],
        [KeyboardButton(text="Инициатива"), KeyboardButton(text="Надёжность")],
        [KeyboardButton(text="Скорость"), KeyboardButton(text="Эмпатия")],
        [KeyboardButton(text="Системность"), KeyboardButton(text="Креативность")],
        [KeyboardButton(text="Открытость"), KeyboardButton(text="Амбициозность")]
    ],
    resize_keyboard=True
)

role_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Исполнитель")],
        [KeyboardButton(text="Заказчик")],
        [KeyboardButton(text="Координатор")],
        [KeyboardButton(text="Инвестор")]
    ],
    resize_keyboard=True
)

format_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Текст"), KeyboardButton(text="Голос")],
        [KeyboardButton(text="Видео"), KeyboardButton(text="Любой")]
    ],
    resize_keyboard=True
)

# --- ИНИЦИАЛИЗАЦИЯ БОТА ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    logger.info(f"📨 /start от {message.from_user.id}")
    await state.set_state(Form.text)
    await message.answer(
        "👋 Привет! Ты вступаешь в Civis — республику профессионалов.\n\n"
        "📝 Расскажи о себе и своей профессиональной цели.\n"
        "Минимум 300 символов. Это поможет нам понять твой профиль.",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Form.text)
async def process_text(message: types.Message, state: FSMContext):
    if len(message.text) < 300:
        await message.answer("⚠️ Минимум 300 символов.")
        return
    await state.update_data(text=message.text)
    await state.set_state(Form.values)
    await message.answer(
        "🎯 Выбери 3 ключевые ценности:",
        reply_markup=values_keyboard
    )

@dp.message(Form.values)
async def process_values(message: types.Message, state: FSMContext):
    await state.update_data(values=message.text)
    await state.set_state(Form.role)
    await message.answer(
        "💼 Твоя роль?",
        reply_markup=role_keyboard
    )

@dp.message(Form.role)
async def process_role(message: types.Message, state: FSMContext):
    await state.update_data(role=message.text)
    await state.set_state(Form.format)
    await message.answer(
        "📱 Формат общения?",
        reply_markup=format_keyboard
    )

@dp.message(Form.format)
async def process_format(message: types.Message, state: FSMContext):
    await state.update_data(format=message.text)
    data = await state.get_data()

    success = save_profile(
        tg_user_id=str(message.from_user.id),
        tg_username=message.from_user.username or "unknown",
        text=data.get('text', ''),
        values=data.get('values', ''),
        role=data.get('role', ''),
        format=data.get('format', '')
    )

    if success:
        await message.answer(
            "✅ Ты в Civis!\n\n"
            "Твой профиль сохранён.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await message.answer("⚠️ Ошибка сохранения.", reply_markup=ReplyKeyboardRemove())

    await state.clear()

# --- ЗАПУСК ---
async def main():
    logger.info("🚀 Запуск бота Civis...")
    try:
        me = await bot.me()
        logger.info(f"✅ Бот подключен: @{me.username}")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
