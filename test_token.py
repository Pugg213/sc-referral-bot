#!/usr/bin/env python3
"""
Простой тест для проверки токена бота
"""
import os
import asyncio
import aiohttp

async def test_bot_token():
    token = os.getenv("BOT_TOKEN", "").strip()
    
    if not token:
        print("❌ BOT_TOKEN не найден в переменных окружения")
        return False
    
    print(f"🔍 Проверяем токен длиной {len(token)} символов")
    print(f"🔍 Токен начинается с: {token[:15]}...")
    
    # Тестируем токен через прямой HTTP запрос к Telegram API
    url = f"https://api.telegram.org/bot{token}/getMe"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        bot_info = data.get("result", {})
                        print(f"✅ Токен работает!")
                        print(f"📱 Бот: @{bot_info.get('username')} ({bot_info.get('first_name')})")
                        print(f"🆔 ID: {bot_info.get('id')}")
                        return True
                    else:
                        print(f"❌ Telegram API вернул ошибку: {data}")
                        return False
                elif response.status == 401:
                    print("❌ Токен недействителен (401 Unauthorized)")
                    return False
                else:
                    print(f"❌ HTTP ошибка: {response.status}")
                    text = await response.text()
                    print(f"❌ Ответ: {text}")
                    return False
        except asyncio.TimeoutError:
            print("❌ Таймаут при подключении к Telegram API")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Запуск теста токена бота...")
    result = asyncio.run(test_bot_token())
    if result:
        print("✅ Тест пройден успешно!")
    else:
        print("❌ Тест не пройден")