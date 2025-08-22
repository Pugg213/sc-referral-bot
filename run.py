#!/usr/bin/env python3
"""
КРИТИЧЕСКОЕ РЕШЕНИЕ DEPLOYMENT ПРОБЛЕМЫ
Simplified production entry point для Replit deployment
"""
import os
import sys
import asyncio
import logging

# КРИТИЧНО: NO FORCED PRODUCTION FLAGS - PREVENTS WEBHOOK SWITCHING
# Removed REPL_DEPLOYMENT=1 as it caused webhook URL conflicts
os.environ["PORT"] = "5000"
os.environ["HOST"] = "0.0.0.0"

# Ensure current directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def run_production_bot():
    """Run production bot с прямым import"""
    
    # Setup production logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("🔥 PRODUCTION DEPLOYMENT STARTING")
    logger.info("=" * 50)
    logger.info("📊 Environment Variables:")
    logger.info(f"   REPL_DEPLOYMENT: {os.getenv('REPL_DEPLOYMENT')}")
    logger.info(f"   PORT: {os.getenv('PORT')}")
    logger.info(f"   HOST: {os.getenv('HOST')}")
    logger.info(f"   REPL_SLUG: {os.getenv('REPL_SLUG', 'workspace')}")
    logger.info("=" * 50)
    
    try:
        # Import main bot function
        from main import main as bot_main
        
        logger.info("✅ Bot module imported successfully")
        
        # Run the bot
        await bot_main()
        
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(run_production_bot())
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"❌ DEPLOYMENT ERROR: {e}")
        sys.exit(1)