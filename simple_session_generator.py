#!/usr/bin/env python3
"""
Простой генератор SESSION_STRING для Replit консоли
Использует переменные окружения вместо интерактивного ввода
"""

import asyncio
import os
from telethon import TelegramClient

async def generate_session():
    print("🔐 Простой генератор SESSION_STRING для Telegram бота")
    print("📋 Используйте переменные окружения или уже настроенные секреты")
    
    # Получаем API данные из переменных окружения
    api_id = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    
    if not api_id or not api_hash:
        print("\n❌ ОШИБКА: TG_API_ID и TG_API_HASH не найдены!")
        print("🔑 Эти секреты уже настроены в вашем Replit проекте")
        print("✅ Запускайте этот скрипт - он должен автоматически работать")
        return
    
    print(f"✅ API_ID найден: {api_id}")
    print(f"✅ API_HASH найден: {api_hash[:8]}...")
    
    # Создаем клиент
    client = TelegramClient('session_generator', int(api_id), api_hash)
    
    try:
        print("\n📱 Подключаемся к Telegram...")
        await client.start()
        
        print("✅ Успешно подключились!")
        
        # Получаем session string
        session_string = client.session.save()
        
        print("\n🎉 SESSION_STRING сгенерирован!")
        print("📋 Скопируйте эту строку и обновите секрет SESSION_STRING:")
        print("-" * 60)
        print(session_string)
        print("-" * 60)
        
        print("\n💾 КАК ОБНОВИТЬ:")
        print("1. 🔐 Secrets (в левой панели Replit)")
        print("2. 🔍 Найдите SESSION_STRING")  
        print("3. ✏️ Edit → Вставьте новую строку")
        print("4. 💾 Save")
        print("5. 🔄 Перезапустите бота")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("💡 Возможные решения:")
        print("- Проверьте правильность TG_API_ID и TG_API_HASH")
        print("- Убедитесь что у вас есть интернет подключение")
        
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(generate_session())