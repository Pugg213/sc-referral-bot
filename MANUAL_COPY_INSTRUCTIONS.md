# 📋 Ручное копирование проекта на сервер

## 🎯 Создай эти файлы на своем сервере:

### 1️⃣ requirements.txt
```
aiogram>=3.21.0
aiohttp>=3.12.15
python-dotenv>=1.0.1
requests>=2.32.5
telethon>=1.40.0
```

### 2️⃣ .env (твои настройки)
```
BOT_TOKEN=твой_токен_бота
TG_API_ID=твой_api_id
TG_API_HASH=твой_api_hash
SESSION_STRING=будет_создан_позже
HOST=0.0.0.0
PORT=5000
WEBHOOK_URL=https://твой-домен.com/webhook
```

### 3️⃣ start.py (главный файл запуска)
```python
#!/usr/bin/env python3
import os
import sys
import asyncio
import logging

# Setup environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if not os.getenv("HOST"):
    os.environ["HOST"] = "0.0.0.0"
if not os.getenv("PORT"):
    os.environ["PORT"] = "5000"

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 SC Referral Bot Starting...")
    
    # Import main bot
    from main import main as bot_main
    await bot_main()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🗂️ Затем скопируй ДИРЕКТОРИИ с Replit:

### Основные директории:
- `app/` - весь код бота
- `src/` - React фронтенд  
- `public/` - статические файлы
- `assets/` - ресурсы

### Файлы конфигурации:
- `main.py` - основной файл бота
- `bot.db` - база данных с пользователями
- `package.json` - фронтенд зависимости
- `tonconnect-manifest.json` - TON Connect
- `vite.config.js` - сборка фронтенда

## 🔧 Команды для запуска:

```bash
# Установить зависимости
pip install -r requirements.txt

# Создать SESSION_STRING
python -c "
from telethon import TelegramClient
import os

API_ID = os.getenv('TG_API_ID')  
API_HASH = os.getenv('TG_API_HASH')
client = TelegramClient('session', API_ID, API_HASH)
client.start()
print('SESSION_STRING:', client.session.save())
"

# Запустить бота
python start.py
```

🎯 **ЭТО МИНИМУМ ДЛЯ ЗАПУСКА!**