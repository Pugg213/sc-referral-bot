import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Загружаем .env файл если он есть (для локального тестирования)
load_dotenv()

@dataclass
class CapsuleReward:
    """Структура награды в капсуле"""
    name: str
    amount: float
    probability: float  # от 0 до 1

@dataclass
class RiskThresholds:
    """Пороги для скоринга рисков"""
    captcha_time_min: float = 3.0  # минимальное время решения капчи (сек)
    captcha_time_max: float = 120.0  # максимальное время решения капчи (сек)
    quarantine_hours: int = 1   # часы карантина для новых рефералов (уменьшено до 1 часа)
    max_refs_per_hour: int = 5  # максимум рефералов в час
    max_refs_per_day: int = 20  # максимум рефералов в день
    min_account_age_days: int = 7  # минимальный возраст аккаунта в днях

@dataclass
class Settings:
    BOT_TOKEN: str
    REQUIRED_CHANNEL_ID: str
    REQUIRED_GROUP_ID: str
    CHANNEL_LINK: str = ""
    GROUP_LINK: str = ""
    DB_PATH: str = "bot.db"
    ADMIN_IDS: List[int] = field(default_factory=list)
    SKIP_GROUP_CHECK: bool = False  # Проверять группу (бот добавлен)
    DISABLE_ADMIN_NOTIFICATIONS: bool = True  # Отключить автоматические уведомления админу
    
    # Настройки капсул и наград
    CAPSULE_REWARDS: List[CapsuleReward] = field(default_factory=list)
    DAILY_CAPSULE_LIMIT: int = 3
    MINIMUM_WITHDRAWAL: float = 1000.0
    
    # Настройки рисков
    RISK_THRESHOLDS: RiskThresholds = field(default_factory=RiskThresholds)
    
    def __post_init__(self):
        if not self.ADMIN_IDS:
            self.ADMIN_IDS = []
            
        if not self.CAPSULE_REWARDS:
            self.CAPSULE_REWARDS = [
                CapsuleReward("SC", 0.5, 0.25),   # 25% - 0.5 SC
                CapsuleReward("SC", 1.0, 0.20),   # 20% - 1.0 SC  
                CapsuleReward("SC", 2.0, 0.15),   # 15% - 2.0 SC
                CapsuleReward("SC", 3.0, 0.10),   # 10% - 3.0 SC
                CapsuleReward("SC", 5.0, 0.08),   # 8% - 5 SC
                CapsuleReward("SC", 10.0, 0.05),  # 5% - 10 SC
                CapsuleReward("Пустышка", 0.0, 0.10),      # 10% - ничего
                CapsuleReward("Бонусная капсула", 1.0, 0.05),  # 5% - дополнительная капсула
                CapsuleReward("Удача x2", 0.0, 0.02),      # 2% - удвоение следующей награды
            ]
            
        if not isinstance(self.RISK_THRESHOLDS, RiskThresholds):
            self.RISK_THRESHOLDS = RiskThresholds()
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Загрузка настроек из переменных окружения"""
        admin_ids = []
        
        # Добавляем главного админа из MAIN_ADMIN_ID
        main_admin_str = os.getenv("MAIN_ADMIN_ID", "")
        if main_admin_str:
            try:
                admin_ids.append(int(main_admin_str))
            except ValueError:
                pass
        
        # Добавляем дополнительных админов из ADMIN_IDS
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            try:
                additional_ids = [int(x.strip()) for x in admin_ids_str.split(",")]
                admin_ids.extend(additional_ids)
            except ValueError:
                pass
                
        return cls(
            BOT_TOKEN=os.getenv("BOT_TOKEN", ""),
            REQUIRED_CHANNEL_ID=os.getenv("REQUIRED_CHANNEL_ID", ""),
            REQUIRED_GROUP_ID=os.getenv("REQUIRED_GROUP_ID", ""),
            CHANNEL_LINK=os.getenv("CHANNEL_LINK", ""),
            GROUP_LINK=os.getenv("GROUP_LINK", ""),
            DB_PATH=os.getenv("DB_PATH", "bot.db"),
            ADMIN_IDS=admin_ids
        )
