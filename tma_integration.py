"""
TMA Integration Server - serves both bot (port 5000) and TMA (port 80)
"""
import asyncio
from aiohttp import web, web_runner
import logging
import os

async def setup_tma_routes(app):
    """Setup TMA static file serving routes"""
    
    # Serve TMA static files
    app.router.add_static('/', 'dist', name='tma_static')
    
    # Serve manifest
    async def serve_manifest(request):
        return web.FileResponse('public/tonconnect-manifest.json')
    
    async def serve_icon(request):
        return web.FileResponse('public/icon.svg')
    
    app.router.add_get('/tonconnect-manifest.json', serve_manifest)
    app.router.add_get('/icon.svg', serve_icon)
    
    logging.info("TMA routes configured")

async def run_tma_server():
    """Run integrated TMA server"""
    app = web.Application()
    await setup_tma_routes(app)
    
    # Start TMA server on port 80 (for Telegram Mini Apps)
    runner = web_runner.AppRunner(app)
    await runner.setup()
    
    site = web_runner.TCPSite(runner, '0.0.0.0', 80)
    await site.start()
    
    logging.info("🌐 TMA Server running on port 80")
    logging.info("📱 Ready for Telegram Mini App integration")
    
    # Keep running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Check if dist exists
    if not os.path.exists("dist"):
        logging.error("❌ dist/ folder not found. Run 'npm run build' first.")
        exit(1)
    
    try:
        asyncio.run(run_tma_server())
    except KeyboardInterrupt:
        logging.info("TMA Server stopped")
    except Exception as e:
        logging.error(f"TMA Server error: {e}")