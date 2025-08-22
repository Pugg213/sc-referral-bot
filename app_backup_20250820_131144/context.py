"""
Контекст приложения для передачи зависимостей между модулями
"""
from typing import Optional
from app.config import Settings
from app.db import Database

# Глобальные переменные для хранения контекста
_config: Optional[Settings] = None
_database: Optional[Database] = None

def set_context(cfg: Settings, db: Database):
    """Установить глобальный контекст приложения"""
    global _config, _database
    _config = cfg
    _database = db

def get_config() -> Settings:
    """Получить конфигурацию"""
    if _config is None:
        raise RuntimeError("Configuration not initialized")
    return _config

def get_db() -> Database:
    """Получить экземпляр базы данных"""
    if _database is None:
        raise RuntimeError("Database not initialized")
    return _database
