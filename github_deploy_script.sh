#!/bin/bash
# 🚀 SC REFERRAL BOT - АВТОМАТИЧЕСКАЯ УСТАНОВКА
# Этот скрипт автоматически загружает и настраивает проект

set -e  # Остановиться при ошибке

echo "🚀 SC REFERRAL BOT - АВТОМАТИЧЕСКАЯ УСТАНОВКА"
echo "=============================================="

# Проверка системы
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.11+"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ Git не найден. Установите git"
    exit 1
fi

# Создание рабочей директории
WORK_DIR="$HOME/sc-bot-$(date +%Y%m%d)"
echo "📁 Создаю рабочую директорию: $WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Создание структуры проекта
echo "📋 Создаю структуру проекта..."

# Основные файлы Python
cat > requirements.txt << 'EOF'
aiogram>=3.21.0
aiohttp>=3.12.15
python-dotenv>=1.0.1
requests>=2.32.5
telethon>=1.40.0
EOF

cat > .env.example << 'EOF'
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here
TG_API_ID=your_api_id_here
TG_API_HASH=your_api_hash_here
SESSION_STRING=your_session_string_here

# Server Configuration
HOST=0.0.0.0
PORT=5000
WEBHOOK_URL=https://yourdomain.com/webhook
DATABASE_PATH=./bot.db
CUSTOM_DOMAIN=yourdomain.com
EOF

# Создание основного файла запуска
cat > start_server.py << 'EOF'
#!/usr/bin/env python3
"""
🚀 SC REFERRAL BOT - SERVER STARTUP
"""
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

def check_required_env():
    """Check required environment variables"""
    required_vars = ["BOT_TOKEN", "TG_API_ID", "TG_API_HASH", "SESSION_STRING"]
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print("❌ ОШИБКА: Не найдены переменные окружения:")
        for var in missing:
            print(f"   - {var}")
        print("\n💡 Создайте файл .env со всеми переменными")
        return False
    return True

async def run_bot():
    """Run the bot"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 SC REFERRAL BOT STARTING...")
    logger.info(f"🌐 Host: {os.getenv('HOST', '0.0.0.0')}")
    logger.info(f"🔌 Port: {os.getenv('PORT', '5000')}")
    
    try:
        from main import main as bot_main
        logger.info("✅ Bot modules loaded")
        await bot_main()
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("💡 Убедитесь что все файлы скопированы правильно")
        raise
    except Exception as e:
        logger.error(f"❌ Runtime error: {e}")
        raise

def main():
    """Main entry point"""
    print("🔧 Checking environment...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded")
    except ImportError:
        print("⚠️ python-dotenv not found, using system environment")
    
    if not check_required_env():
        sys.exit(1)
    
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

# Создание простого генератора SESSION_STRING
cat > simple_session_generator.py << 'EOF'
#!/usr/bin/env python3
"""
🔐 Простой генератор SESSION_STRING для Telegram бота
"""
import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

async def main():
    print("🔐 Простой генератор SESSION_STRING для Telegram бота")
    print("="*60)
    
    # Получение API данных
    api_id = os.getenv('TG_API_ID') or input("📱 TG_API_ID: ")
    api_hash = os.getenv('TG_API_HASH') or input("🔑 TG_API_HASH: ")
    
    if not api_id or not api_hash:
        print("❌ Необходимы TG_API_ID и TG_API_HASH")
        return
    
    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ TG_API_ID должен быть числом")
        return
    
    print(f"\n✅ API_ID: {api_id}")
    print(f"✅ API_HASH: {api_hash[:8]}...")
    
    # Создание клиента
    client = TelegramClient(StringSession(), api_id, api_hash)
    
    print("\n📱 Подключаемся к Telegram...")
    await client.connect()
    
    if not await client.is_user_authorized():
        phone = input("📞 Введите номер телефона: ")
        await client.send_code_request(phone)
        code = input("📩 Введите код из Telegram: ")
        await client.sign_in(phone, code)
    
    session_string = client.session.save()
    await client.disconnect()
    
    print("\n" + "="*60)
    print("🎉 SESSION_STRING СОЗДАН!")
    print("="*60)
    print(f"SESSION_STRING={session_string}")
    print("="*60)
    print("\n💡 Скопируйте эту строку в ваш .env файл")

if __name__ == "__main__":
    asyncio.run(main())
EOF

echo "✅ Основные файлы созданы"

# Создание виртуального окружения
echo "🔧 Создаю виртуальное окружение..."
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo "📦 Устанавливаю зависимости..."
pip install -r requirements.txt

echo ""
echo "🎉 БАЗОВАЯ СТРУКТУРА ГОТОВА!"
echo "=============================================="
echo "📁 Проект создан в: $WORK_DIR"
echo ""
echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
echo "1. cd $WORK_DIR"
echo "2. Скопируйте полный код бота в эту директорию"
echo "3. cp .env.example .env"
echo "4. nano .env  # Настройте переменные"
echo "5. python simple_session_generator.py  # Создайте SESSION_STRING"
echo "6. python start_server.py  # Запустите бота"
echo ""
echo "💡 Для полного кода используйте один из способов:"
echo "   - Скачайте архив sc-bot-FULL-*.tar.gz"
echo "   - Клонируйте из GitHub после настройки"
echo ""
echo "🚀 ГОТОВО К РАЗВЕРТЫВАНИЮ!"
EOF

chmod +x github_deploy_script.sh