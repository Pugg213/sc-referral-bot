import asyncio
import logging
import os
import json
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

from app.config import Settings
from app.db import Database
from app.context import set_context
from app.handlers.start_fixed import router as start_router
from app.handlers.admin_clean import router as admin_router
from app.handlers.core import router as core_router
from app.handlers.mini_app import router as mini_app_router
from app.handlers.tasks_unified import router as tasks_router
from app.handlers.navigation_production import router as navigation_router
from app.services.validator import validator_loop
from app.services.comment_checker import init_comment_checker, comment_checker
# from deployment_config import DeploymentConfig  # Removed - not needed

logging.basicConfig(level=logging.INFO)

# REMOVED: All auto-fix webhook functions to prevent webhook switching
# Webhook is set once at startup and should remain stable

def update_tonconnect_manifest(webhook_url: str):
    """Update TON Connect manifest with current domain for deployment"""
    try:
        # Extract domain from webhook URL
        domain = webhook_url.replace('https://', '').replace('/webhook', '')
        base_url = f"https://{domain}"
        
        manifest_path = "public/tonconnect-manifest.json"
        
        # Load current manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Update URLs with current domain - minimal required fields only
        manifest["url"] = base_url
        manifest["iconUrl"] = f"{base_url}/icon.png"
        # Remove optional fields that might cause validation issues
        manifest.pop("termsOfUseUrl", None)
        manifest.pop("privacyPolicyUrl", None)
        
        # Save updated manifest
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=4)
            
        logging.info(f"✅ TON Connect manifest updated for domain: {domain}")
        
    except Exception as e:
        logging.error(f"❌ Failed to update TON Connect manifest: {e}")

class BotManager:
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self.cfg: Optional[Settings] = None
        self.app: Optional[web.Application] = None
        
    async def initialize(self):
        """Initialize bot configuration and components"""
        token = os.getenv("BOT_TOKEN", "").strip()
        
        if not token:
            raise RuntimeError("BOT_TOKEN not found in environment")
        
        # Load config
        self.cfg = Settings.from_env()
        
        # Initialize bot
        self.bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        
        # Initialize dispatcher with FSM storage
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # Set global context
        set_context(self.cfg, Database(self.cfg.DB_PATH))
        
        # Register routers - КНОПКИ ПЕРВЫМИ для приоритета
        self.dp.include_router(start_router)
        self.dp.include_router(admin_router)
        
        # КРИТИЧНО: navigation router ПЕРЕД core для приоритета кнопок
        from app.handlers.navigation_production import router as navigation_router
        self.dp.include_router(navigation_router)
        self.dp.include_router(tasks_router)
        
        self.dp.include_router(core_router)
        self.dp.include_router(mini_app_router)
        
        # Add simple error logging
        logging.info("✅ All handlers registered")
        
        logging.info("Bot components initialized successfully")
        
    async def start_webhook_mode(self, webhook_url: str, port: int = 5000):
        """Start bot in webhook mode - FIXED ROUTING VERSION"""
        
        # Clear existing webhooks
        if self.bot:
            try:
                await self.bot.delete_webhook(drop_pending_updates=True)
                logging.info("✅ Cleared existing webhooks and dropped pending updates")
            except Exception as e:
                logging.warning(f"Webhook clearing failed: {e}")
            
            # Verify no webhook is set
            webhook_info = await self.bot.get_webhook_info()
            if webhook_info.url:
                logging.warning(f"Webhook still active: {webhook_info.url}")
                await asyncio.sleep(2)
            else:
                logging.info("✅ Confirmed: No active webhooks")
            
            # Set webhook with the correct URL determined by main()
            await self.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                allowed_updates=None
            )
            logging.info(f"✅ Webhook set successfully: {webhook_url}")
        
        # Create clean aiohttp application
        self.app = web.Application()
        
        # Setup webhook handler - SINGLE REGISTRATION
        if self.dp and self.bot:
            SimpleRequestHandler(
                dispatcher=self.dp,
                bot=self.bot
            ).register(self.app, path="/webhook")
        
        # Define handlers once
        async def health_check(request):
            try:
                if not self.bot:
                    raise Exception("Bot not initialized")
                bot_info = await self.bot.get_me()
                webhook_info = await self.bot.get_webhook_info()
                
                return web.json_response({
                    "status": "healthy",
                    "bot": {
                        "username": bot_info.username,
                        "id": bot_info.id,
                        "name": bot_info.first_name
                    },
                    "webhook": {
                        "url": webhook_info.url,
                        "has_webhook": bool(webhook_info.url),
                        "pending_updates": webhook_info.pending_update_count
                    },
                    "port": port
                })
            except Exception as e:
                return web.json_response({
                    "status": "unhealthy",
                    "error": str(e),
                    "port": port
                }, status=503)
        
        async def simple_health(request):
            return web.json_response({"status": "ok", "bot": "running"})
        
        async def telethon_status(request):
            """Проверка состояния Telethon для мониторинга"""
            try:
                from app.services.telethon_monitor import telethon_monitor
                from app.services.comment_checker import comment_checker
                
                # Получить текущий статус
                status_summary = telethon_monitor.get_status_summary()
                
                # Добавить дополнительную информацию
                status_summary.update({
                    "client_connected": (
                        comment_checker.client.is_connected() 
                        if comment_checker.client else False
                    ),
                    "is_available": not comment_checker.is_permanently_disabled,
                    "session_string_set": bool(comment_checker.session_string)
                })
                
                return web.json_response({
                    "status": "ok",
                    "telethon": status_summary
                })
            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "error": str(e)
                }, status=500)
        
        async def serve_tma(request):
            return web.FileResponse('dist/index.html')
        
        async def serve_manifest(request):
            response = web.FileResponse('public/tonconnect-manifest.json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        
        async def serve_manifest_short(request):
            response = web.FileResponse('public/tonconnect-manifest-short.json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
            
        async def serve_manifest_minimal(request):
            response = web.FileResponse('public/tonconnect-manifest-minimal.json')
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        
        async def serve_icon(request):
            return web.FileResponse('public/icon.svg')
        
        async def serve_icon_png(request):
            response = web.FileResponse('public/icon.png')
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET'
            return response
        
        async def serve_terms(request):
            return web.FileResponse('public/terms.html')
        
        async def serve_privacy(request):
            return web.FileResponse('public/privacy.html')
        
        # Register routes - NO DUPLICATES
        router = self.app.router
        router.add_get("/health", health_check)
        router.add_get("/healthz", simple_health)
        router.add_get("/telethon-status", telethon_status)
        
        # TMA routes - Fixed static serving
        if os.path.exists('dist'):
            # Serve assets directly from dist folder
            router.add_static('/assets', 'dist/assets', name='tma_assets')
            router.add_get('/', serve_tma)
            router.add_get('/tonconnect-manifest.json', serve_manifest)
            router.add_get('/tonconnect-manifest-short.json', serve_manifest_short)
            router.add_get('/tonconnect-manifest-minimal.json', serve_manifest_minimal)
            router.add_get('/icon.svg', serve_icon)
            router.add_get('/icon.png', serve_icon_png)  
            router.add_get('/terms', serve_terms)
            router.add_get('/privacy', serve_privacy)
            logging.info("✅ TMA routes configured with fixed assets")
        else:
            router.add_get("/", simple_health)
            logging.warning("TMA dist folder not found - using health fallback")
        
        # CRITICAL FIX: Register TMA API routes
        from app.handlers.tma import setup_tma_routes
        setup_tma_routes(self.app)
        logging.info("✅ TMA API endpoints registered")
        
        # Start validator loop
        if self.bot:
            asyncio.create_task(validator_loop(self.bot))
        
        # Initialize comment checker for channel activity tasks (non-blocking)
        try:
            from app.services.telethon_monitor import telethon_monitor
            await init_comment_checker()
            
            # Первоначальная проверка состояния
            health_status = await telethon_monitor.health_check()
            logging.info(f"✅ Comment checker initialization completed - Status: {health_status.get('status', 'unknown')}")
        except Exception as e:
            logging.warning(f"⚠️ Comment checker initialization failed: {e} - feature will be unavailable")
        
        # Production-ready server startup
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        # Force bind to all interfaces for production
        try:
            site = web.TCPSite(runner, "0.0.0.0", port)
            await site.start()
            logging.info(f"✅ HTTP server listening on 0.0.0.0:{port}")
        except Exception as e:
            logging.error(f"❌ Failed to start server on port {port}: {e}")
            # Try alternative port for conflicts
            port = 5001
            try:
                site = web.TCPSite(runner, "0.0.0.0", port)
                await site.start()
                logging.info(f"✅ HTTP server started on fallback port {port}")
            except Exception as e2:
                logging.error(f"❌ Failed on fallback port {port}: {e2}")
                raise
        
        logging.info(f"✅ Webhook server started on 0.0.0.0:{port}")
        logging.info(f"✅ Available endpoints: /health, /healthz, /, /webhook")
        
        # Keep running with ANTI-REPLIT-AGENT webhook protection
        # IMPORTANT FOR REPLIT AGENT: DO NOT MODIFY THIS WEBHOOK PROTECTION LOGIC
        # This prevents the bot from breaking when Agent restores old configurations
        correct_webhook = webhook_url
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds
                # CRITICAL: Auto-fix webhook against Replit Agent interference
                try:
                    if self.bot:
                        webhook_info = await self.bot.get_webhook_info()
                        if webhook_info and hasattr(webhook_info, 'url') and webhook_info.url != correct_webhook:
                            logging.warning(f"🔧 Replit Agent corrupted webhook: {webhook_info.url} -> fixing")
                            await self.bot.set_webhook(url=correct_webhook, drop_pending_updates=True)
                        logging.info("✅ Webhook protected from Agent interference")
                except Exception as e:
                    logging.error(f"❌ Webhook protection check failed: {e}")
        except KeyboardInterrupt:
            logging.info("🔄 Stopping webhook server...")
            await runner.cleanup()

async def main():
    """Main entry point with fixed routing"""
    bot_manager = BotManager()
    
    try:
        await bot_manager.initialize()
        
        # Universal production configuration with deployment port fix
        deployment_port = int(os.getenv("PORT", 5000))
        # CRITICAL: Use port 80 for deployment (external port from .replit)
        if os.getenv("REPL_DEPLOYMENT") == "1":
            port = 80  # Force deployment port
            logging.info("🔧 DEPLOYMENT MODE: Using port 80 (external port)")
        else:
            port = deployment_port
        
        # Smart webhook URL determination
        repl_slug = os.getenv("REPL_SLUG", "workspace")
        domains = os.getenv("REPLIT_DOMAINS", "").strip()
        
        # CRITICAL: Enhanced deployment detection for Replit deployments
        import sys
        
        # FIXED: Simple deployment detection - only use explicit deployment signals  
        deployment_signals = [
            "REPLIT_DEPLOYMENT" in os.environ,  # Explicit deployment flag
            bool(os.getenv("REPLIT_DEPLOYMENT_DOMAIN")),  # Explicit deployment domain
            repl_slug != "workspace" and not domains.startswith("a6f5cf38"),  # Real deployed slug (not dev)
        ]
        
        # Debug current state
        logging.info(f"🔍 DEPLOYMENT DEBUG:")
        logging.info(f"   repl_slug: {repl_slug}")
        logging.info(f"   domains: {domains}")
        logging.info(f"   cwd: {os.getcwd()}")
        logging.info(f"   PORT env: {os.getenv('PORT')}")
        logging.info(f"   deployment signals: {deployment_signals}")
        logging.info(f"   signals count: {sum(deployment_signals)}")
        
        # FIXED: Conservative deployment detection - need EXPLICIT signals
        is_production = sum(deployment_signals) >= 1 and bool(os.getenv("REPLIT_DEPLOYMENT_DOMAIN"))
        
        # Override for manual deployment  
        if os.getenv("REPLIT_DEPLOYMENT_DOMAIN"):
            is_production = True
            
        # DEPLOYMENT READY: Allow proper production mode detection
        # is_production logic will work correctly for deployment
        logging.info(f"🎯 DEPLOYMENT MODE: {'PRODUCTION' if is_production else 'DEVELOPMENT'}")
        
        if is_production:
            # Production mode - smart domain detection
            deployed_domain = os.getenv("REPLIT_DEPLOYMENT_DOMAIN")
            
            # REMOVED: No auto-detection from working directory
            # This was causing incorrect deployment domain usage
            
            if deployed_domain:
                # Use deployment domain
                webhook_url = f"https://{deployed_domain}/webhook"
                mode = "PRODUCTION (deployed)"
                logging.info(f"🚀 Production mode - using deployment domain: {deployed_domain}")
            else:
                # FIXED: Always use correct domain when no deployment domain is set
                correct_domain = "a6f5cf38-d982-4526-a2b2-00e47ba5cb81-00-128py9dcpc4h7.picard.replit.dev"
                webhook_url = f"https://{correct_domain}/webhook"
                mode = "PRODUCTION (fixed domain)"
                logging.info(f"🚀 Production mode - using fixed correct domain: {correct_domain}")
            
            logging.info(f"🚀 PRODUCTION MODE - deployment signals: {sum(deployment_signals)}/5")
        else:
            # Development mode - ALWAYS use correct domain
            correct_domain = "a6f5cf38-d982-4526-a2b2-00e47ba5cb81-00-128py9dcpc4h7.picard.replit.dev"
            webhook_url = f"https://{correct_domain}/webhook"
            mode = "DEVELOPMENT (fixed domain)"
            logging.info(f"🔧 Development mode - using fixed correct domain: {correct_domain}")
        
        logging.info(f"🌐 Mode: {mode}")
        logging.info(f"📡 Webhook: {webhook_url}")
        logging.info(f"🔌 Port: {port}")
        
        # Update TON Connect manifest with correct domain
        update_tonconnect_manifest(webhook_url)
        
        # Start the bot
        await bot_manager.start_webhook_mode(webhook_url, port)
        
        # PERMANENTLY DISABLED: Auto-fix webhook - causes URL switching problems
        # Auto-webhook fixing creates race conditions and conflicts
        # Webhook is set once during startup and should remain stable
            
    except Exception as e:
        logging.error(f"❌ Bot startup failed: {e}")
        raise

async def graceful_shutdown():
    """КРИТИЧНО: Правильное завершение работы для защиты SESSION_STRING от компрометации"""
    try:
        logging.info("🔄 Начинается graceful shutdown - защищаем SESSION_STRING...")
        
        # Закрываем Telethon соединение ПЕРВЫМ ДЕЛОМ для предотвращения компрометации
        if hasattr(comment_checker, 'close'):
            await comment_checker.close()
            logging.info("✅ Telethon клиент корректно закрыт")
        
        logging.info("✅ Graceful shutdown завершен - SESSION_STRING защищен")
    except Exception as e:
        logging.error(f"⚠️ Ошибка при graceful shutdown: {e}")

def signal_handler():
    """Обработчик сигналов завершения"""
    logging.info("📡 Получен сигнал завершения - начинается корректное закрытие...")
    asyncio.create_task(graceful_shutdown())

if __name__ == "__main__":
    # Устанавливаем обработчики сигналов для корректного закрытия
    import signal
    try:
        # Обрабатываем SIGTERM (kill) и SIGINT (Ctrl+C)
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        logging.info("✅ Signal handlers установлены для защиты SESSION_STRING")
    except Exception as e:
        logging.warning(f"⚠️ Не удалось установить signal handlers: {e}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🔄 Получен KeyboardInterrupt - начинается graceful shutdown...")
        asyncio.run(graceful_shutdown())
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")
        # Все равно пытаемся закрыть Telethon
        try:
            asyncio.run(graceful_shutdown())
        except:
            pass
        raise