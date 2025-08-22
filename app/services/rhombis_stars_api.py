"""
Rhombis Stars API Integration - Настоящий API для премиум функций
Документация: https://api.rhombis.app/#tag/stars
"""
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class RhombisStarsAPI:
    """Клиент для работы с Rhombis Stars API"""
    
    def __init__(self):
        self.base_url = "https://api.rhombis.app"
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить HTTP сессию"""
        if self.session is None or self.session.closed:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "SC-Referral-Bot/1.0"
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Базовый запрос к Rhombis API"""
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.request(method, url, json=(data or {}), timeout=timeout) as response:
                if response.status == 200:
                    result = await response.json()
                    return {"success": True, "data": result}
                else:
                    error_text = await response.text()
                    logger.error(f"Rhombis API error {response.status}: {error_text}")
                    return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                    
        except asyncio.TimeoutError:
            logger.error("Rhombis API timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Rhombis API network error: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_stars_balance(self, user_id: str) -> Dict[str, Any]:
        """Получить баланс звезд пользователя"""
        endpoint = f"/stars/balance/{user_id}"
        return await self._request("GET", endpoint)
    
    async def create_stars_transaction(self, transaction_data: Dict) -> Dict[str, Any]:
        """Создать транзакцию со звездами"""
        endpoint = "/stars/transactions"
        return await self._request("POST", endpoint, transaction_data)
    
    async def get_user_purchases(self, user_id: str) -> Dict[str, Any]:
        """Получить покупки пользователя"""
        endpoint = f"/stars/purchases/{user_id}"
        return await self._request("GET", endpoint)
    
    async def verify_purchase(self, purchase_id: str) -> Dict[str, Any]:
        """Проверить статус покупки"""
        endpoint = f"/stars/verify/{purchase_id}"
        return await self._request("GET", endpoint)
    
    async def create_premium_subscription(self, subscription_data: Dict) -> Dict[str, Any]:
        """Создать премиум подписку через Stars"""
        endpoint = "/stars/subscriptions"
        
        # Подготавливаем данные для API
        api_data = {
            "user_id": str(subscription_data.get("telegram_id")),
            "username": subscription_data.get("username", ""),
            "subscription_type": subscription_data.get("plan"),
            "duration_days": subscription_data.get("duration", 30),
            "stars_amount": int(subscription_data.get("price", 0) * 100),  # Конвертируем в звезды
            "metadata": {
                "first_name": subscription_data.get("first_name", ""),
                "last_name": subscription_data.get("last_name", ""),
                "source": "sc_referral_bot"
            }
        }
        
        return await self._request("POST", endpoint, api_data)
    
    async def activate_channel_access(self, access_data: Dict) -> Dict[str, Any]:
        """Активировать доступ к каналу через Stars"""
        endpoint = "/stars/channels/access"
        
        api_data = {
            "user_id": str(access_data.get("user_id")),
            "channel_id": access_data.get("channel_key"),
            "stars_amount": int(access_data.get("price", 0) * 100),
            "duration_days": access_data.get("duration", 30)
        }
        
        return await self._request("POST", endpoint, api_data)
    
    async def purchase_telegram_premium(self, premium_data: Dict) -> Dict[str, Any]:
        """Покупка Telegram Premium через Rhombis API"""
        endpoint = "/premium/telegram"
        
        api_data = {
            "user_id": str(premium_data.get("telegram_id")),
            "username": premium_data.get("username", ""),
            "duration_months": premium_data.get("duration_months", 1),
            "stars_amount": int(premium_data.get("stars_price", 0)),
            "premium_features": premium_data.get("features", []),
            "metadata": {
                "first_name": premium_data.get("first_name", ""),
                "last_name": premium_data.get("last_name", ""),
                "source": "sc_referral_bot_tma"
            }
        }
        
        return await self._request("POST", endpoint, api_data)
    
    async def get_available_products(self) -> Dict[str, Any]:
        """Получить доступные продукты и услуги"""
        endpoint = "/stars/products"
        return await self._request("GET", endpoint)
    
    async def close_session(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()

# Глобальный экземпляр
_rhombis_stars_api = None

def get_rhombis_stars_api() -> RhombisStarsAPI:
    """Получить экземпляр Rhombis Stars API"""
    global _rhombis_stars_api
    if _rhombis_stars_api is None:
        _rhombis_stars_api = RhombisStarsAPI()
    return _rhombis_stars_api

# Продукты через Stars API (реальная интеграция)
RHOMBIS_STARS_PRODUCTS = {
    "premium_subscriptions": [
        {
            "id": "premium_weekly",
            "title": "Weekly Premium",
            "stars_price": 50,  # 50 звезд
            "duration": 7,
            "benefits": [
                "10 daily capsules instead of 3",
                "2x task rewards multiplier", 
                "VIP status badge",
                "Priority support access"
            ]
        },
        {
            "id": "premium_monthly", 
            "title": "Monthly Premium",
            "stars_price": 200,  # 200 звезд
            "duration": 30,
            "benefits": [
                "All Weekly features included",
                "Exclusive premium channel access",
                "Personal account manager",
                "Early feature previews"
            ],
            "popular": True
        },
        {
            "id": "premium_yearly",
            "title": "Yearly Premium", 
            "stars_price": 2000,  # 2000 звезд
            "duration": 365,
            "benefits": [
                "All Monthly features included",
                "Personal trading signals",
                "Exclusive NFT rewards", 
                "VIP community events"
            ]
        }
    ],
    "channel_access": [
        {
            "id": "vip_trading",
            "title": "VIP Trading Signals",
            "stars_price": 100,
            "duration": 30,
            "channel": "@sc_vip_trading",
            "description": "Professional trading signals and market analysis"
        },
        {
            "id": "alpha_investments",
            "title": "Alpha Investment Opportunities", 
            "stars_price": 150,
            "duration": 30,
            "channel": "@sc_alpha_invest",
            "description": "Early access to investment opportunities"
        },
        {
            "id": "insider_news",
            "title": "Insider News & Updates",
            "stars_price": 80,
            "duration": 30, 
            "channel": "@sc_insider_news",
            "description": "Exclusive news and project updates"
        }
    ],
    "telegram_premium": [
        {
            "id": "telegram_premium_1m",
            "title": "Telegram Premium - 1 Month",
            "stars_price": 250,
            "duration_months": 1,
            "features": [
                "Increased upload limit (2GB)",
                "Faster download speed",
                "Voice-to-text conversion",
                "Advanced chat management",
                "Premium stickers and reactions",
                "No ads in public channels"
            ]
        },
        {
            "id": "telegram_premium_3m", 
            "title": "Telegram Premium - 3 Months",
            "stars_price": 700,
            "duration_months": 3,
            "features": [
                "All 1-month features included",
                "Better value (save 50 stars)",
                "Extended premium benefits",
                "Priority customer support"
            ],
            "popular": True
        },
        {
            "id": "telegram_premium_12m",
            "title": "Telegram Premium - 12 Months", 
            "stars_price": 2500,
            "duration_months": 12,
            "features": [
                "All premium features included",
                "Best value (save 500 stars)",
                "Full year of premium access",
                "VIP support priority"
            ]
        }
    ]
}