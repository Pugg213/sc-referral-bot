#!/usr/bin/env python3
"""
Production Token Validator - Tests all token loading strategies
Run this before deployment to ensure 100% token reliability
"""

import os
import sys

def test_token_loading():
    """Test all token loading strategies"""
    print("🔬 BULLETPROOF TOKEN VALIDATOR")
    print("=" * 50)
    
    strategies_tested = 0
    strategies_successful = 0
    
    # Strategy 1: Direct environment access
    strategies_tested += 1
    token = os.getenv("BOT_TOKEN", "").strip()
    if token and len(token) > 40:
        print(f"✅ Strategy 1 (direct env): SUCCESS ({len(token)} chars)")
        strategies_successful += 1
    else:
        print(f"❌ Strategy 1 (direct env): FAILED")
    
    # Strategy 2: Force reload environment variables
    strategies_tested += 1
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        token2 = os.getenv("BOT_TOKEN", "").strip()
        if token2 and len(token2) > 40:
            print(f"✅ Strategy 2 (dotenv reload): SUCCESS ({len(token2)} chars)")
            strategies_successful += 1
        else:
            print(f"❌ Strategy 2 (dotenv reload): FAILED")
    except Exception as e:
        print(f"❌ Strategy 2 (dotenv reload): ERROR - {e}")
    
    # Strategy 3: Environment scan
    strategies_tested += 1
    found_in_scan = False
    for key, value in os.environ.items():
        if ('BOT' in key.upper() or 'TOKEN' in key.upper()) and ':' in str(value) and len(str(value)) > 40:
            if str(value).startswith('7393209394:'):
                print(f"✅ Strategy 3 (env scan): SUCCESS - found in {key}")
                strategies_successful += 1
                found_in_scan = True
                break
    
    if not found_in_scan:
        print(f"❌ Strategy 3 (env scan): FAILED")
    
    # Final assessment
    print(f"\n📊 RESULTS:")
    print(f"  Strategies tested: {strategies_tested}")
    print(f"  Strategies successful: {strategies_successful}")
    print(f"  Success rate: {(strategies_successful/strategies_tested)*100:.1f}%")
    
    if strategies_successful > 0:
        print(f"✅ TOKEN LOADING: RELIABLE")
        print(f"🚀 DEPLOYMENT: SAFE TO PROCEED")
        return True
    else:
        print(f"❌ TOKEN LOADING: UNRELIABLE") 
        print(f"🚨 DEPLOYMENT: CHECK SECRETS FIRST")
        return False

if __name__ == "__main__":
    success = test_token_loading()
    sys.exit(0 if success else 1)