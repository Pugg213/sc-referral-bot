"""
Сервис генерации и проверки капч
"""
import random
import time
from datetime import datetime
from typing import Tuple, Optional

from app.context import get_db
from app.keyboards import get_captcha_keyboard

class CaptchaService:
    def __init__(self):
        self.operations = ['+', '-', '*']
    
    async def generate_captcha(self, user_id: int) -> Tuple[int, str, any]:
        """Сгенерировать математическую капчу"""
        db = get_db()
        
        # Генерируем простую математическую задачу
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        operation = random.choice(self.operations)
        
        if operation == '+':
            correct_answer = num1 + num2
        elif operation == '-':
            # Убедимся, что результат положительный
            if num1 < num2:
                num1, num2 = num2, num1
            correct_answer = num1 - num2
        else:  # multiplication
            # Для умножения используем меньшие числа
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            correct_answer = num1 * num2
        
        # Сохранить сессию капчи
        session_id = db.save_captcha_session(user_id, str(correct_answer))
        
        # Генерируем варианты ответов
        options = self.generate_answer_options(correct_answer)
        
        # Создать клавиатуру
        keyboard = get_captcha_keyboard(session_id, options)
        
        captcha_text = f"🧮 <b>Решите пример:</b>\n\n<code>{num1} {operation} {num2} = ?</code>"
        
        return session_id, captcha_text, keyboard
    
    def generate_answer_options(self, correct_answer: int) -> list:
        """Сгенерировать варианты ответов для капчи"""
        options = [correct_answer]
        
        # Добавить неправильные варианты
        while len(options) < 6:
            # Варианты рядом с правильным ответом
            wrong_answer = correct_answer + random.randint(-5, 5)
            
            # Избегаем отрицательных чисел и дубликатов
            if wrong_answer > 0 and wrong_answer not in options:
                options.append(wrong_answer)
        
        # Перемешать варианты
        random.shuffle(options)
        return options
    
    async def check_captcha(self, session_id: int, user_answer: int) -> Tuple[bool, float]:
        """Проверить ответ на капчу"""
        db = get_db()
        
        session = db.get_captcha_session(session_id)
        if not session:
            return False, 0.0
        
        if session['solved']:
            return False, 0.0  # Капча уже решена
        
        # Вычислить время решения
        start_time = datetime.fromisoformat(session['start_time'])
        solve_time = (datetime.now() - start_time).total_seconds()
        
        # Проверить правильность ответа
        correct_answer = int(session['captcha_value'])
        is_correct = user_answer == correct_answer
        
        if is_correct:
            # Отметить капчу как решенную
            db.complete_captcha(session_id, solve_time)
        
        return is_correct, solve_time
    
    def calculate_captcha_score(self, solve_time: float, risk_thresholds) -> float:
        """Вычислить скор качества решения капчи"""
        min_time = risk_thresholds.captcha_time_min
        max_time = risk_thresholds.captcha_time_max
        
        if solve_time < min_time:
            # Слишком быстро - подозрительно (возможно бот)
            return 0.1
        elif solve_time > max_time:
            # Слишком медленно - тоже подозрительно
            return 0.3
        else:
            # Нормальное время - высокий скор
            # Оптимальное время около 10-30 секунд
            optimal_time = 20.0
            time_diff = abs(solve_time - optimal_time)
            score = max(0.5, 1.0 - (time_diff / optimal_time))
            return min(1.0, score)
