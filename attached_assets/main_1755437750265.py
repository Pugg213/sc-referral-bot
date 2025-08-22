import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.config import Settings
from app.db import Database
from app.context import set_context
from app.handlers.start import router as start_router
from app.handlers.core import router as core_router
from app.handlers.admin import router as admin_router
from app.services.validator import validator_loop

logging.basicConfig(level=logging.INFO)

async def main():
    cfg = Settings.from_env()
    bot = Bot(token=cfg.BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    db = Database(cfg.DB_PATH)
    db.init()

    set_context(cfg=cfg, db=db)

    # Routers
    dp.include_router(start_router)
    dp.include_router(core_router)
    dp.include_router(admin_router)

    # Background validator loop
    asyncio.create_task(validator_loop(bot))

    logging.info("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
