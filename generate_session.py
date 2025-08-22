#!/usr/bin/env python3
"""
Интерактивный генератор SESSION_STRING для Telegram
Работает в любом окружении с правильным вводом данных
"""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

def get_api_credentials():
    """Получает API данные от пользователя"""
    print("🔐 Генератор SESSION_STRING для Telegram бота")
    print("📋 Вам понадобятся данные из https://my.telegram.org")
    print()
    
    # Запрашиваем API_ID
    while True:
        try:
            api_id_input = input("📱 Введите ваш API_ID (число): ").strip()
            api_id = int(api_id_input)
            break
        except ValueError:
            print("❌ API_ID должен быть числом. Попробуйте снова.")
    
    # Запрашиваем API_HASH
    api_hash = input("🔑 Введите ваш API_HASH: ").strip()
    
    if not api_hash:
        print("❌ API_HASH не может быть пустым")
        return None, None
    
    return api_id, api_hash

async def phone_code_callback():
    """Запрашивает код подтверждения"""
    return input("📨 Введите код из Telegram: ").strip()

async def generate_session():
    """Генерирует SESSION_STRING для Telethon"""
    
    # Получаем API данные
    api_id, api_hash = get_api_credentials()
    if not api_id or not api_hash:
        return
    
    print()
    print(f"✅ API_ID: {api_id}")
    print(f"✅ API_HASH: {api_hash[:8]}...")
    print()
    
    # Создаем клиент с пустой строкой сессии
    client = TelegramClient(StringSession(), api_id, api_hash)
    
    try:
        print("🔄 Подключение к Telegram...")
        
        # Запрашиваем номер телефона
        phone = input("📞 Введите номер телефона (с кодом страны, например +7): ").strip()
        
        # Авторизация с обработкой кода
        await client.start(
            phone=phone,
            code_callback=phone_code_callback
        )
        
        print("✅ Успешно авторизовались в Telegram!")
        
        # Получаем строку сессии
        session_string = client.session.save()
        
        print()
        print("🎯 ВАШ SESSION_STRING ГОТОВ:")
        print("=" * 80)
        print(session_string)
        print("=" * 80)
        print()
        print("📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Скопируйте строку выше")
        print("2. Добавьте в Deployment Settings:")
        print("   - Name: SESSION_STRING")
        print("   - Value: [вся строка выше]")
        print("3. Нажмите 'Save' и перезапустите deployment")
        print("4. ✅ Telethon заработает автоматически!")
        print()
        print("⚠️  ВАЖНО:")
        print("- Никому не передавайте эту строку")
        print("- Используйте только в одном проекте")
        print("- При компрометации - сгенерируйте новую")
        
    except Exception as e:
        print(f"❌ ОШИБКА при генерации сессии: {e}")
        if "phone number" in str(e).lower():
            print("💡 Проверьте правильность формата номера телефона")
        elif "code" in str(e).lower():
            print("💡 Проверьте правильность кода из Telegram")
        else:
            print("💡 Проверьте правильность API_ID и API_HASH")
        
    finally:
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(generate_session())
    except KeyboardInterrupt:
        print("\n🛑 Генерация прервана пользователем")