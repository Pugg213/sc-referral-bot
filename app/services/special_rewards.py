"""
Система специальных наград для капсул
"""
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from app.context import get_db

class SpecialRewardService:
    """Сервис для обработки специальных наград"""
    
    def process_special_reward(self, user_id: int, reward_name: str, amount: float) -> Dict[str, Any]:
        """Обработать специальную награду"""
        db = get_db()
        
        if reward_name == "Пустышка":
            return {
                "message": "😔 Капсула оказалась пустой! Попробуйте еще раз.",
                "emoji": "💔",
                "special": True
            }
        
        elif reward_name == "Бонусная капсула":
            # Добавить дополнительную капсулу на сегодня
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET bonus_capsules = bonus_capsules + 1
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
            
            return {
                "message": "🎁 Бонусная капсула! Вы получили дополнительную попытку на сегодня!",
                "emoji": "🎁",
                "special": True
            }
        
        elif reward_name == "Удача x2":
            # Активировать удвоение на следующие 10 минут
            expires = datetime.now() + timedelta(minutes=10)
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET luck_multiplier = 2.0, luck_expires = ?
                    WHERE user_id = ?
                """, (expires.isoformat(), user_id))
                conn.commit()
            
            return {
                "message": "🍀 Удача x2 активирована! Следующие награды будут удвоены на 10 минут!",
                "emoji": "🍀",
                "special": True
            }
        
        else:
            # Обычная награда SC
            current_multiplier = self.get_luck_multiplier(user_id)
            final_amount = amount * current_multiplier
            
            # Добавить к балансу
            db.add_balance(user_id, final_amount)
            
            message_parts = []
            if current_multiplier > 1.0:
                message_parts.append(f"🍀 Удача x{current_multiplier}!")
                message_parts.append(f"🎁 {amount} SC → {final_amount} SC")
                # Сбросить удачу после использования
                self.reset_luck_multiplier(user_id)
            else:
                message_parts.append(f"🎁 Награда: {final_amount} SC")
            
            return {
                "message": "\n".join(message_parts),
                "emoji": "💰",
                "amount": final_amount,
                "special": False
            }
    
    def get_luck_multiplier(self, user_id: int) -> float:
        """Получить текущий множитель удачи"""
        db = get_db()
        user = db.get_user(user_id)
        
        if not user or not user.get('luck_expires'):
            return 1.0
        
        # Проверить, не истек ли срок действия
        expires = datetime.fromisoformat(user['luck_expires'])
        if datetime.now() > expires:
            self.reset_luck_multiplier(user_id)
            return 1.0
        
        return user.get('luck_multiplier', 1.0)
    
    def reset_luck_multiplier(self, user_id: int):
        """Сбросить множитель удачи"""
        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET luck_multiplier = 1.0, luck_expires = NULL
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
    
    def get_available_capsules(self, user_id: int) -> int:
        """Получить количество доступных капсул с учетом бонусных"""
        from app.context import get_config
        db = get_db()
        cfg = get_config()
        user = db.get_user(user_id)
        
        if not user:
            return 0
        
        # Базовый лимит из конфига + рефералы
        base_limit = cfg.DAILY_CAPSULE_LIMIT + (user.get('validated_referrals', 0) or 0)
        
        # Добавить бонусные капсулы
        bonus_capsules = user.get('bonus_capsules', 0) or 0
        
        total_limit = base_limit + bonus_capsules
        
        # Проверить сколько уже открыто сегодня
        opened_today = user.get('daily_capsules_opened', 0) or 0
        
        # Если дата не сегодня, сбросить счетчик
        from datetime import datetime
        today = datetime.now().date().isoformat()
        last_date = user.get('last_capsule_date')
        
        if last_date != today:
            opened_today = 0
        
        # Вернуть оставшиеся капсулы
        remaining = max(0, total_limit - opened_today)
        return remaining
    
    def use_bonus_capsule(self, user_id: int):
        """Использовать бонусную капсулу"""
        db = get_db()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET bonus_capsules = CASE 
                    WHEN bonus_capsules > 0 THEN bonus_capsules - 1 
                    ELSE 0 
                END
                WHERE user_id = ? AND bonus_capsules > 0
            """, (user_id,))
            conn.commit()
            
            return cursor.rowcount > 0