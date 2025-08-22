#!/usr/bin/env python3
"""
Быстрый тест - попробуем новый токен вручную
"""
import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def test_new_token(token):
    """Тест нового токена"""
    try:
        bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        bot_info = await bot.get_me()
        print(f"✅ Токен работает!")
        print(f"📱 Бот: @{bot_info.username} ({bot_info.first_name})")
        print(f"🆔 ID: {bot_info.id}")
        await bot.session.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

# Замените этот токен на ваш новый
NEW_TOKEN = "7393209394:AAFXGamauF3PaaTYcyHW6Bxn_sJPyfptAcU"

if __name__ == "__main__":
    if NEW_TOKEN == "ВВЕДИТЕ_ВАШ_НОВЫЙ_ТОКЕН_ЗДЕСЬ":
        print("❗ Замените NEW_TOKEN на ваш новый токен в файле quick_test.py")
    else:
        print(f"🔍 Тестируем токен: {NEW_TOKEN[:20]}...")
        result = asyncio.run(test_new_token(NEW_TOKEN))
        if result:
            print("✅ Новый токен работает! Теперь нужно обновить секреты Replit")
        else:
            print("❌ Токен не работает, проверьте правильность")