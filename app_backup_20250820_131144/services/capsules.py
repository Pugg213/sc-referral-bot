"""
Сервис работы с капсулами и наградами
"""
import random
import logging
from typing import Optional, List

from app.config import CapsuleReward

class CapsuleService:
    """Сервис для работы с капсулами"""
    
    def open_capsule(self, rewards: List[CapsuleReward]) -> Optional[CapsuleReward]:
        """Открыть капсулу и получить случайную награду"""
        if not rewards:
            logging.error("No rewards configured for capsules")
            return None
        
        # Проверить, что сумма вероятностей равна 1.0
        total_probability = sum(reward.probability for reward in rewards)
        if abs(total_probability - 1.0) > 0.001:
            logging.warning(f"Total probability is not 1.0: {total_probability}")
        
        # Генерируем случайное число от 0 до 1
        rand = random.random()
        
        # Проходим по наградам и выбираем на основе вероятности
        cumulative_prob = 0.0
        for reward in rewards:
            cumulative_prob += reward.probability
            if rand <= cumulative_prob:
                logging.info(f"Capsule opened: {reward.amount} {reward.name} (probability: {reward.probability})")
                return reward
        
        # Если по какой-то причине не выбрали награду, возвращаем последнюю
        logging.warning("Fallback to last reward in capsule opening")
        return rewards[-1] if rewards else None
    
    def get_reward_statistics(self, rewards: List[CapsuleReward]) -> dict:
        """Получить статистику наград"""
        if not rewards:
            return {}
        
        total_value = sum(reward.amount * reward.probability for reward in rewards)
        
        stats = {
            'total_rewards': len(rewards),
            'expected_value': total_value,
            'min_reward': min(reward.amount for reward in rewards),
            'max_reward': max(reward.amount for reward in rewards),
            'most_likely': max(rewards, key=lambda r: r.probability),
            'rarest': min(rewards, key=lambda r: r.probability)
        }
        
        return stats
    
    def validate_rewards_config(self, rewards: List[CapsuleReward]) -> List[str]:
        """Валидация конфигурации наград"""
        errors = []
        
        if not rewards:
            errors.append("No rewards configured")
            return errors
        
        total_probability = sum(reward.probability for reward in rewards)
        if abs(total_probability - 1.0) > 0.001:
            errors.append(f"Total probability is not 1.0: {total_probability}")
        
        for i, reward in enumerate(rewards):
            if reward.probability <= 0:
                errors.append(f"Reward {i}: probability must be positive")
            
            if reward.amount <= 0:
                errors.append(f"Reward {i}: amount must be positive")
            
            if not reward.name:
                errors.append(f"Reward {i}: name cannot be empty")
        
        return errors
