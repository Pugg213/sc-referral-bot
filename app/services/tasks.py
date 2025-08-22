"""
Система заданий от партнеров
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class TaskType(Enum):
    CHANNEL_SUBSCRIPTION = "channel_subscription"
    GROUP_JOIN = "group_join" 
    WEBSITE_VISIT = "website_visit"
    SOCIAL_FOLLOW = "social_follow"
    DAILY_LOGIN = "daily_login"
    REFERRAL_MILESTONE = "referral_milestone"
    CHANNEL_ACTIVITY = "channel_activity"  # Новый тип: активность в канале

class TaskStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    PAUSED = "paused"

@dataclass
class Task:
    id: int
    title: str
    description: str
    task_type: TaskType
    reward_sc: float
    reward_capsules: int
    partner_name: str
    partner_url: str
    requirements: Dict[str, Any]  # Специфические требования задания
    # Для CHANNEL_ACTIVITY: 
    # - channel: @username канала
    # - min_comments: минимум комментариев
    # - period_days: период в днях
    # - min_posts: минимум постов с комментариями
    # - start_date: дата начала
    expires_at: Optional[datetime]
    max_completions: Optional[int]  # Максимальное количество выполнений
    current_completions: int = 0
    status: TaskStatus = TaskStatus.ACTIVE
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class TaskService:
    """Сервис управления заданиями"""
    
    def __init__(self, db):
        self.db = db
        self._init_default_tasks()
    
    def _init_default_tasks(self):
        """Инициализация базовых заданий"""
        default_tasks = [
            Task(
                id=1,
                title="🎯 Ежедневный вход",
                description="Заходите в бота каждый день и получайте бонус!",
                task_type=TaskType.DAILY_LOGIN,
                reward_sc=10.0,
                reward_capsules=1,
                partner_name="SC Referral Bot",
                partner_url="",
                requirements={"consecutive_days": 1},
                expires_at=None,  # Не истекает
                max_completions=None  # Неограниченно
            ),
            Task(
                id=2,
                title="👥 Пригласи 5 друзей",
                description="Пригласите 5 активных друзей и получите мега-награду!",
                task_type=TaskType.REFERRAL_MILESTONE,
                reward_sc=100.0,
                reward_capsules=5,
                partner_name="SC Referral Bot",
                partner_url="",
                requirements={"referral_count": 5},
                expires_at=None,
                max_completions=1  # Только один раз
            ),
            Task(
                id=3,
                title="📺 Подпишись на SC Channel",
                description="Подпишитесь на официальный канал SC и получите бонус",
                task_type=TaskType.CHANNEL_SUBSCRIPTION,
                reward_sc=25.0,
                reward_capsules=2,
                partner_name="SC Project",
                partner_url="https://t.me/sc_official",
                requirements={"channel_id": "@sc_official"},
                expires_at=datetime.now() + timedelta(days=30),
                max_completions=1
            ),
        ]
        
        # Добавить задания в БД если их нет (отключено для стабильности)
        # for task in default_tasks:
        #     if not self.db.get_task(task.id):
        #         self.db.add_task(task)
    
    def get_available_tasks(self, user_id: int) -> List[Task]:
        """Получить доступные задания для пользователя"""
        all_tasks = self.db.get_active_tasks()
        user_completed = self.db.get_user_completed_tasks(user_id)
        completed_task_ids = {tc['task_id'] for tc in user_completed}
        
        available_tasks = []
        for task in all_tasks:
            # Проверить истечение срока
            if task.expires_at and datetime.now() > task.expires_at:
                continue
                
            # Проверить лимит выполнений
            if task.max_completions and task.id in completed_task_ids:
                continue
                
            # Проверить требования
            if self._check_task_requirements(user_id, task):
                available_tasks.append(task)
        
        return available_tasks
    
    def _check_task_requirements(self, user_id: int, task: Task) -> bool:
        """Проверить выполнение требований задания"""
        if task.task_type == TaskType.DAILY_LOGIN:
            # Ежедневные задания всегда доступны
            return True
            
        elif task.task_type == TaskType.REFERRAL_MILESTONE:
            user = self.db.get_user(user_id)
            if not user:
                return False
            required_refs = task.requirements.get("referral_count", 0)
            return user['validated_referrals'] >= required_refs
            
        elif task.task_type == TaskType.CHANNEL_SUBSCRIPTION:
            # Требует проверки подписки на конкретный канал
            return True  # Проверка будет при выполнении
        
        elif task.task_type == TaskType.CHANNEL_ACTIVITY:
            # Задания на активность в канале всегда доступны зарегистрированным пользователям
            return True
            
        return True
    
    async def complete_task(self, user_id: int, task_id: int, bot = None) -> Dict[str, Any]:
        """Выполнить задание"""
        task = self.db.get_task(task_id)
        if not task:
            return {"success": False, "error": "Задание не найдено"}
        
        # Проверить доступность
        available_tasks = self.get_available_tasks(user_id)
        if task.id not in [t.id for t in available_tasks]:
            return {"success": False, "error": "Задание недоступно"}
        
        # Проверить уже выполненные
        if self.db.is_task_completed(user_id, task_id):
            return {"success": False, "error": "Задание уже выполнено"}
        
        # Выполнить проверку в зависимости от типа
        verification_result = await self._verify_task_completion(user_id, task, bot)
        if not verification_result["success"]:
            return verification_result
        
        # Записать выполнение
        self.db.complete_user_task(user_id, task_id)
        
        # Выдать награды
        self.db.update_user_balance(user_id, task.reward_sc)
        if task.reward_capsules > 0:
            self.db.add_bonus_capsules(user_id, task.reward_capsules)
        
        return {
            "success": True,
            "task": task,
            "reward_sc": task.reward_sc,
            "reward_capsules": task.reward_capsules
        }
    
    async def _verify_task_completion(self, user_id: int, task: Task, bot = None) -> Dict[str, Any]:
        """Проверить выполнение задания"""
        if task.task_type == TaskType.DAILY_LOGIN:
            # Проверить последний вход
            last_login = self.db.get_user_last_login(user_id)
            today = datetime.now().date()
            
            if last_login and last_login.date() == today:
                return {"success": True}
            else:
                # Обновить последний вход
                self.db.update_user_last_login(user_id)
                return {"success": True}
        
        elif task.task_type == TaskType.REFERRAL_MILESTONE:
            user = self.db.get_user(user_id)
            required_refs = task.requirements.get("referral_count", 0)
            
            if user and user['validated_referrals'] >= required_refs:
                return {"success": True}
            else:
                return {"success": False, "error": f"Нужно {required_refs} подтвержденных рефералов"}
        
        elif task.task_type == TaskType.CHANNEL_SUBSCRIPTION:
            if not bot:
                return {"success": False, "error": "Невозможно проверить подписку"}
            
            channel_id = task.requirements.get("channel_id")
            try:
                member = await bot.get_chat_member(channel_id, user_id)
                if member.status in ['member', 'administrator', 'creator']:
                    return {"success": True}
                else:
                    return {"success": False, "error": "Подпишитесь на канал для выполнения задания"}
            except:
                return {"success": False, "error": "Ошибка проверки подписки"}
        
        elif task.task_type == TaskType.CHANNEL_ACTIVITY:
            # Проверка активности в канале через комментарии
            from .comment_checker import comment_checker
            
            channel = task.requirements.get("channel")
            min_comments = task.requirements.get("min_comments", 3)
            period_days = task.requirements.get("period_days", 7)
            start_date = task.requirements.get("start_date")
            
            if not channel:
                return {"success": False, "error": "Канал не указан в задании"}
            
            # Парсим дату начала задания
            if isinstance(start_date, str):
                try:
                    start_date = datetime.fromisoformat(start_date)
                except ValueError:
                    start_date = task.created_at or datetime.now()
            elif not start_date:
                start_date = task.created_at or datetime.now()
            
            # ЗАЩИТА: Graceful fallback при недоступности Telethon
            if not comment_checker.client and not comment_checker.is_permanently_disabled:
                logging.warning("🔧 Telethon клиент не инициализирован, пытаемся переподключиться...")
                init_result = await comment_checker.init_client()
                if not init_result or not comment_checker.client:
                    logging.warning("⚠️ Telethon недоступен - задание на комментарии временно недоступно")
                    return {"success": False, "error": "Проверка комментариев временно недоступна. Попробуйте позже или обратитесь к администратору."}
            elif comment_checker.is_permanently_disabled:
                logging.warning("🔧 Проверка комментариев отключена администратором")
                return {"success": False, "error": "Проверка комментариев временно отключена. Обратитесь к администратору."}
            
            # Проверяем комментарии через Telethon (с поддержкой min_posts)
            min_posts = task.requirements.get("min_posts", 1)  # Минимум постов с комментариями
            
            result = await comment_checker.check_user_comments_in_channel(
                user_id=user_id,
                channel_username=channel,
                min_comments=min_comments,
                period_days=period_days,
                start_date=start_date,
                min_posts=min_posts
            )
            
            if result["success"]:
                if result["meets_requirement"]:
                    return {"success": True}
                else:
                    # Формируем понятное сообщение об ошибке
                    found_comments = result['found_comments']
                    found_posts = result.get('found_posts', 0)
                    
                    if min_posts == 1:
                        error_msg = f"❌ Найдено {found_comments} комментариев. Нужно {min_comments} комментариев"
                    else:
                        error_msg = f"❌ Не хватает активности!\n\n📊 Найдено: {found_comments} комментариев на {found_posts} постах\n🎯 Требуется: {min_comments} комментариев под {min_posts} разными постами\n\n💡 Оставьте комментарии под разными постами в канале!"
                    
                    return {
                        "success": False, 
                        "error": error_msg
                    }
            else:
                return {"success": False, "error": result["error"]}
        
        # КРИТИЧНО: Не засчитывать неизвестные типы заданий автоматически
        return {"success": False, "error": f"Неизвестный тип задания: {task.task_type}"}
    
    def get_user_task_stats(self, user_id: int) -> Dict[str, Any]:
        """Получить статистику заданий пользователя"""
        completed_tasks = self.db.get_user_completed_tasks(user_id)
        available_tasks = self.get_available_tasks(user_id)
        
        total_earned_sc = sum(ct['reward_sc'] for ct in completed_tasks)
        total_earned_capsules = sum(ct['reward_capsules'] for ct in completed_tasks)
        
        return {
            "completed_count": len(completed_tasks),
            "available_count": len(available_tasks),
            "total_earned_sc": total_earned_sc,
            "total_earned_capsules": total_earned_capsules,
            "completed_tasks": completed_tasks,
            "available_tasks": available_tasks
        }