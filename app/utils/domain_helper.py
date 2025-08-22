"""
Domain helper for getting correct URLs in different environments
"""
import os

def get_tma_url():
    """Get TMA URL for current environment - FIXED VERSION"""
    # Always use current REPLIT_DOMAINS for consistency
    replit_domains = os.getenv('REPLIT_DOMAINS', '')
    if replit_domains:
        domain = replit_domains.split(',')[0]
        return f"https://{domain}"
    
    # REMOVED OLD HARDCODED DOMAIN - prevents webhook switching
    # Fallback to localhost for local development
    return "http://localhost:5000"

def get_bot_url():
    """Get bot URL for current environment - FIXED VERSION"""
    replit_domains = os.getenv('REPLIT_DOMAINS', '')
    if replit_domains:
        domain = replit_domains.split(',')[0]
        return f"https://{domain}"
    
    # REMOVED OLD HARDCODED DOMAIN - prevents webhook switching
    return "http://localhost:5000"