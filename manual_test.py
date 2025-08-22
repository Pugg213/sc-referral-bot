#!/usr/bin/env python3
"""
Ручной тест токена - введите новый токен напрямую
"""
import asyncio
import aiohttp

async def test_manual_token():
    print("Введите новый токен бота (или 'q' для выхода):")
    token = input().strip()
    
    if token.lower() == 'q' or not token:
        return
    
    print(f"🔍 Тестируем токен длиной {len(token)} символов")
    print(f"🔍 Токен начинается с: {token[:20]}...")
    
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
                        
                        # Сохраним рабочий токен в .env файл
                        with open('.env', 'w') as f:
                            f.write(f"BOT_TOKEN={token}\n")
                            f.write(f"MAIN_ADMIN_ID=545921\n")
                            f.write(f"REQUIRED_CHANNEL_ID=-1002429972793\n")
                            f.write(f"REQUIRED_GROUP_ID=-1002442392045\n")
                        print("💾 Рабочий токен сохранен в .env файл")
                        return True
                elif response.status == 401:
                    print("❌ Токен недействителен (401 Unauthorized)")
                else:
                    print(f"❌ HTTP ошибка: {response.status}")
                    
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    return False

if __name__ == "__main__":
    print("🚀 Ручной тест токена бота")
    asyncio.run(test_manual_token())