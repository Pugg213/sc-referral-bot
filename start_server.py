#!/usr/bin/env python3
"""
🚀 UNIVERSAL SERVER STARTUP SCRIPT
Для запуска SC Referral Bot на любом сервере
"""
import os
import sys
import asyncio
import logging

def setup_environment():
    """Setup environment for external server"""
    # Ensure current directory is in path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Set default values if not provided
    if not os.getenv("HOST"):
        os.environ["HOST"] = "0.0.0.0"
    if not os.getenv("PORT"):
        os.environ["PORT"] = "5000"

def check_required_env():
    """Check required environment variables"""
    required_vars = [
        "BOT_TOKEN",
        "TG_API_ID", 
        "TG_API_HASH",
        "SESSION_STRING"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print("❌ ОШИБКА: Не найдены переменные окружения:")
        for var in missing:
            print(f"   - {var}")
        print("\n💡 Создайте файл .env со всеми переменными (см. env_example.txt)")
        return False
    return True

async def run_bot():
    """Run the bot on external server"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 SC REFERRAL BOT - EXTERNAL SERVER")
    logger.info("=" * 50)
    logger.info(f"🌐 Host: {os.getenv('HOST', '0.0.0.0')}")
    logger.info(f"🔌 Port: {os.getenv('PORT', '5000')}")
    logger.info(f"🤖 Bot: {os.getenv('BOT_TOKEN', 'NOT_SET')[:20]}...")
    logger.info("=" * 50)
    
    try:
        # Import and run main bot
        from main import main as bot_main
        logger.info("✅ Bot modules loaded")
        
        # Start the bot
        await bot_main()
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("💡 Убедитесь что все зависимости установлены: pip install -r server_requirements.txt")
        raise
    except Exception as e:
        logger.error(f"❌ Runtime error: {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Main entry point"""
    print("🔧 Preparing server environment...")
    setup_environment()
    
    # Load .env file if exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded from .env")
    except ImportError:
        print("⚠️ python-dotenv not found, using system environment")
    except Exception as e:
        print(f"⚠️ Could not load .env: {e}")
    
    # Check environment
    if not check_required_env():
        sys.exit(1)
    
    # Run the bot
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()