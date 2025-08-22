"""
Монитор состояния Telethon соединения для предотвращения проблем с SESSION_STRING
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
from .comment_checker import comment_checker

class TelethonMonitor:
    """Мониторинг состояния Telethon клиента"""
    
    def __init__(self):
        self.last_health_check = None
        self.health_check_interval = 3600  # 1 час
        self.consecutive_failures = 0
        self.max_failures_before_disable = 5
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья Telethon соединения"""
        now = datetime.now()
        
        # Проверяем не слишком ли часто делаем проверки
        if (self.last_health_check and 
            (now - self.last_health_check).total_seconds() < self.health_check_interval):
            return {"status": "skipped", "reason": "too_frequent"}
        
        self.last_health_check = now
        
        try:
            if not comment_checker.client:
                # Пытаемся инициализировать
                init_result = await comment_checker.init_client()
                if init_result:
                    self.consecutive_failures = 0
                    logging.info("✅ Telethon health check: соединение восстановлено")
                    return {"status": "recovered", "client_connected": True}
                else:
                    self.consecutive_failures += 1
                    logging.warning(f"⚠️ Telethon health check: инициализация не удалась (попытка {self.consecutive_failures})")
                    
                    # Отключаем после слишком многих неудач
                    if self.consecutive_failures >= self.max_failures_before_disable:
                        comment_checker.is_permanently_disabled = True
                        logging.error("🚨 Telethon health check: слишком много неудач, отключаем проверку комментариев")
                    
                    return {"status": "failed", "consecutive_failures": self.consecutive_failures}
            else:
                # Клиент есть, проверяем его состояние
                if comment_checker.client.is_connected():
                    try:
                        # Простая проверка авторизации
                        is_authorized = await comment_checker.client.is_user_authorized()
                        if is_authorized:
                            self.consecutive_failures = 0
                            return {"status": "healthy", "client_connected": True, "authorized": True}
                        else:
                            self.consecutive_failures += 1
                            logging.warning("⚠️ Telethon health check: потеряна авторизация")
                            return {"status": "unauthorized", "client_connected": True, "authorized": False}
                    except Exception as e:
                        self.consecutive_failures += 1
                        logging.warning(f"⚠️ Telethon health check: ошибка проверки авторизации: {e}")
                        return {"status": "auth_error", "error": str(e)}
                else:
                    self.consecutive_failures += 1
                    logging.warning("⚠️ Telethon health check: клиент не подключен")
                    return {"status": "disconnected", "client_connected": False}
                        
        except Exception as e:
            self.consecutive_failures += 1
            logging.error(f"❌ Telethon health check: критическая ошибка: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Получить сводку состояния"""
        return {
            "consecutive_failures": self.consecutive_failures,
            "is_permanently_disabled": comment_checker.is_permanently_disabled,
            "has_client": comment_checker.client is not None,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "next_check_in_seconds": (
                self.health_check_interval - 
                (datetime.now() - self.last_health_check).total_seconds()
                if self.last_health_check else 0
            )
        }

# Глобальный экземпляр
telethon_monitor = TelethonMonitor()