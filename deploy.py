#!/usr/bin/env python3
"""
PRODUCTION Deployment Script for SC Referral Bot
Forces production mode for .replit.app deployment
"""
import asyncio
import logging
import sys
import os

# CRITICAL FIX: NO FORCED PRODUCTION FLAGS - USE NORMAL DETECTION
# Removed all forced environment variables that trigger webhook switching
# Let main.py determine deployment mode naturally

# Only set essential production variables
os.environ["PORT"] = "5000"  # Replit requires port 5000
os.environ["HOST"] = "0.0.0.0"  # Allow all connections

print("🚀 SC REFERRAL BOT - PRODUCTION DEPLOYMENT")
print("=" * 60)
print("🔧 STABLE DEPLOYMENT MODE")
print(f"🔌 PORT: {os.environ.get('PORT', '80')}")
print(f"🔌 HOST: {os.environ.get('HOST', '0.0.0.0')}")
print("✅ No forced production flags to prevent webhook switching")
print("✅ Natural deployment mode detection enabled")
print("=" * 60)

# Убедимся что мы в правильной директории
if not os.path.exists('app'):
    workspace_paths = ['/home/runner/workspace', '.']
    for path in workspace_paths:
        if os.path.exists(f'{path}/app'):
            os.chdir(path)
            break

# Добавим текущую директорию в Python path
sys.path.insert(0, os.getcwd())

# Import main function from main.py
try:
    from main import main
    
    def main_entry():
        asyncio.run(main())
        
except ImportError as e:
    print(f"❌ Failed to import main: {e}")
    sys.exit(1)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 DEPLOYMENT SCRIPT STARTING...")
    print(f"📂 Working directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path[0]}")
    
    try:
        main_entry()
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Bot startup failed: {e}")
        sys.exit(1)