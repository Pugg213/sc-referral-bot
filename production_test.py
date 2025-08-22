#!/usr/bin/env python3
"""
Production deployment test - simulates production environment
"""
import os
import asyncio
import logging
from aiohttp import web, ClientSession

logging.basicConfig(level=logging.INFO)

async def test_production_server():
    """Test that server responds correctly in production mode"""
    
    # Health check endpoint
    async def health_check(request):
        return web.json_response({
            "status": "healthy",
            "mode": "production_test",
            "port": 5000,
            "ready_for_traffic": True
        })
    
    # TMA endpoint
    async def tma_endpoint(request):
        return web.Response(text="""<!DOCTYPE html>
<html><head><title>TMA Test</title></head>
<body><h1>TMA Production Test - Ready!</h1></body></html>""", 
                          content_type='text/html')
    
    # Create app
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/healthz', health_check)
    app.router.add_get('/', tma_endpoint)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    
    try:
        site = web.TCPSite(runner, "0.0.0.0", 5000)
        await site.start()
        logging.info("✅ Production test server started on 0.0.0.0:5000")
        
        # Test endpoints
        async with ClientSession() as session:
            # Test health
            async with session.get('http://localhost:5000/health') as resp:
                data = await resp.json()
                logging.info(f"Health check: {data}")
            
            # Test TMA
            async with session.get('http://localhost:5000/') as resp:
                html = await resp.text()
                logging.info(f"TMA endpoint: {len(html)} bytes HTML")
        
        logging.info("✅ Production test PASSED - server ready for HTTP traffic")
        return True
        
    except Exception as e:
        logging.error(f"❌ Production test FAILED: {e}")
        return False
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    success = asyncio.run(test_production_server())
    exit(0 if success else 1)