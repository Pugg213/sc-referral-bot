"""
Утилиты для создания заданий с гибкими настройками
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.services.tasks import TaskType

def create_comment_task(
    title: str,
    description: str,
    partner_name: str,
    partner_url: str,
    channel_username: str,
    min_comments: int,
    period_days: int,
    min_posts: int = 1,
    reward_sc: float = 0.0,
    reward_capsules: int = 1,
    expires_days: Optional[int] = None
) -> Dict[str, Any]:
    """
    Создать задание на комментарии с гибкими настройками
    
    Args:
        title: Название задания
        description: Описание задания
        partner_name: Имя партнера
        partner_url: Ссылка на канал/группу
        channel_username: Username канала (например, @simplecoin_news)
        min_comments: Минимум комментариев нужно оставить
        period_days: За сколько дней задание (срок выполнения)
        min_posts: Минимум постов должно быть прокомментировано
        reward_sc: Награда в SC токенах
        reward_capsules: Награда в бонусных капсулах
        expires_days: Через сколько дней задание истекает (None = не истекает)
    
    Returns:
        Dict с данными для создания задания в базе данных
    """
    
    # Настройка истечения
    expires_at = None
    if expires_days:
        expires_at = datetime.now() + timedelta(days=expires_days)
    
    # Создаем requirements для CHANNEL_ACTIVITY
    requirements = {
        "channel": channel_username,
        "min_comments": min_comments,
        "period_days": period_days,
        "min_posts": min_posts,
        "start_date": datetime.now().isoformat()  # Задание начинается с момента создания
    }
    
    return {
        "title": title,
        "description": description,
        "task_type": TaskType.CHANNEL_ACTIVITY.value,
        "partner_name": partner_name,
        "partner_url": partner_url,
        "reward_sc": reward_sc,
        "reward_capsules": reward_capsules,
        "requirements": requirements,
        "expires_at": expires_at,
        "period_days": period_days,
        "status": "active"
    }

def create_subscription_task(
    title: str,
    description: str,
    partner_name: str,
    partner_url: str,
    channel_id: str,
    reward_sc: float = 0.0,
    reward_capsules: int = 1,
    expires_days: Optional[int] = None
) -> Dict[str, Any]:
    """
    Создать задание на подписку
    
    Args:
        title: Название задания
        description: Описание задания  
        partner_name: Имя партнера
        partner_url: Ссылка на канал/группу
        channel_id: ID канала для проверки подписки
        reward_sc: Награда в SC токенах
        reward_capsules: Награда в бонусных капсулах
        expires_days: Через сколько дней задание истекает
    """
    
    expires_at = None
    if expires_days:
        expires_at = datetime.now() + timedelta(days=expires_days)
    
    requirements = {
        "channel_id": channel_id
    }
    
    return {
        "title": title,
        "description": description,
        "task_type": TaskType.CHANNEL_SUBSCRIPTION.value,
        "partner_name": partner_name,
        "partner_url": partner_url,
        "reward_sc": reward_sc,
        "reward_capsules": reward_capsules,
        "requirements": requirements,
        "expires_at": expires_at,
        "period_days": 1,  # Подписка проверяется мгновенно
        "status": "active"
    }

# Предустановленные шаблоны заданий
TASK_TEMPLATES = {
    "light_comments": {
        "min_comments": 3,
        "period_days": 7,
        "min_posts": 2,
        "reward_sc": 15.0,
        "reward_capsules": 1
    },
    "medium_comments": {
        "min_comments": 5,
        "period_days": 7,
        "min_posts": 3,
        "reward_sc": 25.0,
        "reward_capsules": 2
    },
    "heavy_comments": {
        "min_comments": 10,
        "period_days": 14,
        "min_posts": 5,
        "reward_sc": 50.0,
        "reward_capsules": 5
    }
}