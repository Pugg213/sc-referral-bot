#!/usr/bin/env python3
"""
Post-deployment verification script
Checks all systems after deployment
"""
import asyncio
import logging
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Settings
from app.db import Database

async def verify_deployment():
    """Verify all systems are working after deployment"""
    print("🔍 SC Bot - Post-Deploy Verification")
    print("=" * 50)
    
    # Check environment
    print("📋 Environment Variables:")
    required_vars = ['BOT_TOKEN', 'MAIN_ADMIN_ID', 'REQUIRED_CHANNEL_ID', 'REQUIRED_GROUP_ID']
    for var in required_vars:
        value = os.getenv(var)
        status = "✅" if value else "❌"
        print(f"  {status} {var}: {'SET' if value else 'MISSING'}")
    
    # Check deployment type
    is_deployment = os.getenv('REPL_DEPLOYMENT') == '1'
    domains = os.getenv('REPLIT_DOMAINS', '')
    print(f"\n🌐 Deployment Status:")
    print(f"  Deployment Mode: {'✅ PRODUCTION' if is_deployment else '❌ DEVELOPMENT'}")
    print(f"  Domain: {domains if domains else 'Not set'}")
    
    # Check database
    print(f"\n💾 Database Verification:")
    try:
        cfg = Settings.from_env()
        db = Database(cfg.DB_PATH)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check users
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            # Check balance
            cursor.execute("SELECT SUM(balance) FROM users")
            total_balance = cursor.fetchone()[0] or 0
            
            # Check capsules
            cursor.execute("SELECT COUNT(*) FROM capsule_openings")
            capsule_count = cursor.fetchone()[0]
            
            print(f"  ✅ Users: {user_count}")
            print(f"  ✅ Balance: {total_balance} SC")
            print(f"  ✅ Capsules: {capsule_count}")
            
    except Exception as e:
        print(f"  ❌ Database Error: {e}")
    
    # Check TMA files
    print(f"\n📱 TMA Files:")
    tma_files = [
        'dist/index.html',
        'dist/assets/',
        'public/tonconnect-manifest.json',
        'public/icon.svg',
        'public/terms.html',
        'public/privacy.html'
    ]
    
    for file_path in tma_files:
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path}")
    
    print(f"\n🚀 Deployment Summary:")
    print(f"  Ready for Production: {'✅ YES' if is_deployment and domains else '❌ NO'}")
    print(f"  Webhook URL: https://{domains}/webhook" if domains else "  Webhook URL: Not configured")
    print(f"  TMA URL: https://{domains}/" if domains else "  TMA URL: Not configured")
    
    print("\n" + "=" * 50)
    print("✅ Post-Deploy Verification Complete")

if __name__ == "__main__":
    asyncio.run(verify_deployment())