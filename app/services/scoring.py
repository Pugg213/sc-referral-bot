"""
Сервис скоринга рисков пользователей
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from aiogram import Bot

class RiskScorer:
    """Класс для вычисления риск-скора пользователей"""
    
    async def calculate_risk_score(self, bot: Bot, user_data: Dict[str, Any], thresholds) -> float:
        """Вычислить общий риск-скор пользователя"""
        scores = []
        
        # 1. Возраст аккаунта Telegram
        account_age_score = await self.check_account_age(bot, user_data['user_id'], thresholds)
        scores.append(('account_age', account_age_score, 0.3))
        
        # 2. Качество решения капчи
        captcha_score = user_data.get('captcha_score', 0.5)
        scores.append(('captcha', captcha_score, 0.2))
        
        # 3. Время между регистрацией и подпиской
        subscription_timing_score = self.check_subscription_timing(user_data)
        scores.append(('subscription_timing', subscription_timing_score, 0.2))
        
        # 4. Профиль пользователя (имя, username)
        profile_score = await self.check_profile_quality(bot, user_data['user_id'])
        scores.append(('profile', profile_score, 0.2))
        
        # 5. Активность в каналах
        activity_score = await self.check_channel_activity(bot, user_data['user_id'])
        scores.append(('activity', activity_score, 0.1))
        
        # Вычислить взвешенный риск-скор
        total_weight = sum(weight for _, _, weight in scores)
        risk_score = sum(score * weight for _, score, weight in scores) / total_weight
        
        # Инвертировать скор (чем выше риск, тем больше значение)
        risk_score = 1.0 - risk_score
        
        logging.info(f"Risk score for user {user_data['user_id']}: {risk_score:.3f}")
        logging.debug(f"Individual scores: {[(name, score) for name, score, _ in scores]}")
        
        return risk_score
    
    async def check_account_age(self, bot: Bot, user_id: int, thresholds) -> float:
        """Проверить возраст аккаунта Telegram"""
        try:
            # Получить информацию о пользователе
            user = await bot.get_chat(user_id)
            
            # К сожалению, Telegram Bot API не предоставляет дату создания аккаунта
            # Используем эвристики на основе user_id
            
            # Старые аккаунты имеют меньшие ID (приблизительно)
            # Это очень грубая оценка, но лучше чем ничего
            if user_id < 100000000:  # Очень старые аккаунты
                return 1.0
            elif user_id < 500000000:  # Старые аккаунты
                return 0.8
            elif user_id < 1000000000:  # Средние
                return 0.6
            elif user_id < 5000000000:  # Новые
                return 0.4
            else:  # Очень новые
                return 0.2
                
        except Exception as e:
            logging.error(f"Error checking account age for {user_id}: {e}")
            return 0.5  # Средний скор при ошибке
    
    def check_subscription_timing(self, user_data: Dict[str, Any]) -> float:
        """Проверить время между регистрацией и подпиской"""
        if not user_data.get('registration_date'):
            return 0.5
        
        reg_date = datetime.fromisoformat(user_data['registration_date'])
        now = datetime.now()
        
        time_diff = (now - reg_date).total_seconds()
        
        # Слишком быстрая подписка подозрительна
        if time_diff < 60:  # Меньше минуты
            return 0.2
        elif time_diff < 300:  # Меньше 5 минут
            return 0.4
        elif time_diff < 3600:  # Меньше часа
            return 0.8
        else:  # Больше часа
            return 1.0
    
    async def check_profile_quality(self, bot: Bot, user_id: int) -> float:
        """Проверить качество профиля пользователя"""
        try:
            user = await bot.get_chat(user_id)
            score = 0.5  # Базовый скор
            
            # Проверить наличие имени
            if user.first_name:
                # Проверить качество имени
                name_quality = self.analyze_name_quality(user.first_name)
                score += name_quality * 0.3
            
            # Проверить наличие username
            if user.username:
                username_quality = self.analyze_username_quality(user.username)
                score += username_quality * 0.2
            
            return min(1.0, score)
            
        except Exception as e:
            logging.error(f"Error checking profile quality for {user_id}: {e}")
            return 0.5
    
    def analyze_name_quality(self, name: str) -> float:
        """Анализ качества имени пользователя"""
        if not name:
            return 0.0
        
        score = 0.5
        
        # Проверить длину
        if 2 <= len(name) <= 30:
            score += 0.2
        
        # Проверить на спам-паттерны
        spam_patterns = ['test', 'user', '123', 'bot', 'fake']
        if not any(pattern in name.lower() for pattern in spam_patterns):
            score += 0.3
        
        return min(1.0, score)
    
    def analyze_username_quality(self, username: str) -> float:
        """Анализ качества username"""
        if not username:
            return 0.0
        
        score = 0.5
        
        # Проверить длину
        if 5 <= len(username) <= 32:
            score += 0.2
        
        # Проверить на случайные символы
        if not username.replace('_', '').isalnum():
            score -= 0.1
        
        # Проверить на спам-паттерны
        spam_patterns = ['test', 'user', 'bot', 'fake', '123456']
        if not any(pattern in username.lower() for pattern in spam_patterns):
            score += 0.3
        
        return min(1.0, score)
    
    async def check_channel_activity(self, bot: Bot, user_id: int) -> float:
        """Проверить активность в каналах (ограниченные возможности в Bot API)"""
        try:
            # Bot API не позволяет получить историю активности пользователя
            # Возвращаем средний скор
            return 0.5
        except Exception as e:
            logging.error(f"Error checking channel activity for {user_id}: {e}")
            return 0.5
