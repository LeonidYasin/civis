import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from dotenv import load_dotenv

# --- ЗАГРУЗКА ПЕРЕМЕННЫХ ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")

# --- ПОДКЛЮЧЕНИЕ К БАЗЕ (SQLite) ---
DB_PATH = Path(__file__).parent / "civis_data.db"

def init_db():
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

def save_profile(tg_user_id, tg_username, text, values, role, format):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO profiles (tg_user_id, tg_username, text, selected_values, role, format, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tg_user_id, tg_username, text, values, role, format, datetime.now().isoformat()))
    conn.commit()
    conn.close()

init_db()

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

# --- ИНИЦИАЛИЗАЦИЯ ДИСПЕТЧЕРА ---
dp = Dispatcher()

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.set_state(Form.text)
    await message.answer(
        "Привет! Ты вступаешь в Civis — республику профессионалов.\n\n"
        "Расскажи о себе и своей профессиональной цели.\n"
        "Минимум 300 символов. Это поможет нам понять твой профиль.",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(Form.text)
async def process_text(message: types.Message, state: FSMContext):
    if len(message.text) < 300:
        await message.answer("Пожалуйста, напиши не менее 300 символов. Это важно для анализа.")
        return
    await state.update_data(text=message.text)
    await state.set_state(Form.values)
    await message.answer(
        "Выбери 3 ключевые ценности, которые ты разделяешь в работе:",
        reply_markup=values_keyboard
    )

@dp.message(Form.values)
async def process_values(message: types.Message, state: FSMContext):
    await state.update_data(values=message.text)
    await state.set_state(Form.role)
    await message.answer(
        "Какова твоя основная роль?",
        reply_markup=role_keyboard
    )

@dp.message(Form.role)
async def process_role(message: types.Message, state: FSMContext):
    await state.update_data(role=message.text)
    await state.set_state(Form.format)
    await message.answer(
        "Какой формат общения тебе удобен?",
        reply_markup=format_keyboard
    )

@dp.message(Form.format)
async def process_format(message: types.Message, state: FSMContext):
    await state.update_data(format=message.text)
    data = await state.get_data()

    try:
        save_profile(
            tg_user_id=str(message.from_user.id),
            tg_username=message.from_user.username or "unknown",
            text=data.get('text', ''),
            values=data.get('values', ''),
            role=data.get('role', ''),
            format=data.get('format', '')
        )
        await message.answer(
            "✅ Ты в Civis!\n\n"
            "Твой профиль сохранён. Скоро мы начнём подбирать тебе проекты и команды.\n"
            "Следи за обновлениями.",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        logging.error(e)
        await message.answer("⚠️ Ошибка сохранения. Попробуй позже.")

    await state.clear()

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
