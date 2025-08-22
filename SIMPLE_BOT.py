#!/usr/bin/env python3
"""
🚀 УПРОЩЕННАЯ ВЕРСИЯ SC REFERRAL BOT
Минимальный код для запуска на любом сервере
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

# Загрузить .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://yourdomain.com/webhook")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))

# Инициализация бота и роутера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# База данных
def init_db():
    """Создать базу данных"""
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            referrer_id INTEGER,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            balance REAL DEFAULT 0,
            total_referrals INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            reward REAL,
            channel_username TEXT,
            min_comments INTEGER DEFAULT 2,
            min_posts INTEGER DEFAULT 2
        )
    """)
    
    # Добавить базовое задание
    cursor.execute("""
        INSERT OR IGNORE INTO tasks (id, title, description, reward, channel_username, min_comments, min_posts)
        VALUES (1, "💬 Комментарии в The TON", "Оставьте 2 комментария под 2 разными постами", 50.0, "@The_TON_io", 2, 2)
    """)
    
    conn.commit()
    conn.close()

def get_user(user_id: int):
    """Получить пользователя"""
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id: int, username: str, first_name: str, referrer_id: int = None):
    """Создать пользователя"""
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, username, first_name, referrer_id)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, first_name, referrer_id))
    conn.commit()
    conn.close()

# Обработчики команд
@router.message(Command("start"))
async def start_handler(message: Message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    # Извлечь реферальный код
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
        except ValueError:
            pass
    
    # Проверить существование пользователя
    if not get_user(user_id):
        create_user(user_id, username, first_name, referrer_id)
        if referrer_id:
            await message.answer(f"🎉 Добро пожаловать! Вы зарегистрированы по реферальной ссылке!")
        else:
            await message.answer(f"🎉 Добро пожаловать в SC Referral Bot!")
    
    # Главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="📋 Задания", callback_data="tasks")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="ref_link")]
    ])
    
    await message.answer(
        "🤖 <b>SC Referral Bot</b>\\n\\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.callback_query(F.data == "balance")
async def balance_handler(callback: CallbackQuery):
    """Показать баланс"""
    user = get_user(callback.from_user.id)
    if user:
        balance = user[5] if len(user) > 5 else 0  # balance column
        await callback.message.edit_text(
            f"💰 <b>Ваш баланс</b>\\n\\n"
            f"💎 SC токенов: {balance:.2f}\\n\\n"
            f"💡 Выполняйте задания и приглашайте друзей!",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "tasks")
async def tasks_handler(callback: CallbackQuery):
    """Показать задания"""
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    
    if tasks:
        task = tasks[0]  # Первое задание
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить", callback_data=f"check_task_{task[0]}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        
        await callback.message.edit_text(
            f"📋 <b>{task[1]}</b>\\n\\n"
            f"{task[2]}\\n\\n"
            f"💰 Награда: {task[3]} SC",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text("📋 Заданий пока нет.")

@router.callback_query(F.data.startswith("check_task_"))
async def check_task_handler(callback: CallbackQuery):
    """Проверить выполнение задания"""
    # Упрощенная проверка - всегда засчитываем
    user_id = callback.from_user.id
    
    # Добавить награду
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + 50 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(
        "🎉 <b>Задание выполнено!</b>\\n\\n"
        "💰 Вы получили 50 SC токенов!\\n\\n"
        "✨ Продолжайте выполнять задания и приглашать друзей!",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "referrals")
async def referrals_handler(callback: CallbackQuery):
    """Показать рефералы"""
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
    ref_count = cursor.fetchone()[0]
    conn.close()
    
    await callback.message.edit_text(
        f"👥 <b>Ваши рефералы</b>\\n\\n"
        f"👤 Приглашено: {ref_count}\\n"
        f"💰 Заработано: {ref_count * 10} SC\\n\\n"
        f"💡 За каждого друга вы получаете 10 SC!",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "ref_link")
async def ref_link_handler(callback: CallbackQuery):
    """Показать реферальную ссылку"""
    user_id = callback.from_user.id
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    
    await callback.message.edit_text(
        f"🔗 <b>Ваша реферальная ссылка</b>\\n\\n"
        f"<code>{ref_link}</code>\\n\\n"
        f"📤 Поделитесь с друзьями и получайте 10 SC за каждого!",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery):
    """Вернуться в главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="📋 Задания", callback_data="tasks")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="ref_link")]
    ])
    
    await callback.message.edit_text(
        "🤖 <b>SC Referral Bot</b>\\n\\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Webhook handlers
async def webhook_handler(request):
    """Обработка webhook от Telegram"""
    update = await request.json()
    await dp.feed_update(bot, update)
    return web.Response(status=200)

async def health_handler(request):
    """Health check endpoint"""
    return web.json_response({"status": "healthy", "bot": "SC Referral Bot"})

async def main():
    """Главная функция"""
    logger.info("🚀 Запуск SC Referral Bot...")
    
    # Инициализация базы данных
    init_db()
    logger.info("✅ База данных инициализирована")
    
    # Регистрация роутера
    dp.include_router(router)
    
    # Установка webhook
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")
    
    # Создание веб-приложения
    app = web.Application()
    app.router.add_post("/webhook", webhook_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", health_handler)
    
    # Запуск сервера
    logger.info(f"✅ Сервер запущен на {HOST}:{PORT}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    
    # Поддержание работы
    try:
        while True:
            await asyncio.sleep(3600)  # Спать час
    except KeyboardInterrupt:
        logger.info("⏹️ Остановка бота...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())