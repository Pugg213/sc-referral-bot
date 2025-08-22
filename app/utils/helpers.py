"""
Вспомогательные функции
"""
import re
import logging
from typing import Optional

def extract_referrer_id(start_text: str) -> Optional[int]:
    """Извлечь ID реферера из команды /start"""
    if not start_text:
        return None
    
    # Ищем паттерн ref_USERID
    match = re.search(r'ref_(\d+)', start_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    
    return None

def extract_user_id(user_identifier: str) -> Optional[int]:
    """Извлечь user_id из строки (username или ID)"""
    # Если это число - возвращаем как есть
    if user_identifier.isdigit():
        return int(user_identifier)
    
    # Если это @username - пока не можем преобразовать без Bot API
    # В реальном боте это нужно делать через базу данных или Bot API
    if user_identifier.startswith('@'):
        # Здесь нужна функция поиска в базе по username
        # Пока возвращаем None
        return None
    
    return None

def format_user_mention(first_name: str, username: str = None) -> str:
    """Форматировать упоминание пользователя"""
    if username:
        return f"@{username}"
    elif first_name:
        return first_name
    else:
        return "Пользователь"

def format_balance(amount: float) -> str:
    """Форматировать баланс для отображения"""
    if amount == int(amount):
        return str(int(amount))
    else:
        return f"{amount:.2f}"

def validate_ton_address(address: str) -> bool:
    """Простая валидация TON адреса"""
    if not address:
        return False
    
    # TON адреса обычно начинаются с UQ, EQ или kQ и содержат base64 символы
    if not re.match(r'^[UEkQ][A-Za-z0-9\-_]{46}$', address):
        return False
    
    return True

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Очистить пользовательский ввод"""
    if not text:
        return ""
    
    # Обрезать до максимальной длины
    text = text[:max_length]
    
    # Удалить потенциально опасные символы
    text = re.sub(r'[<>"\']', '', text)
    
    return text.strip()

def format_datetime(dt_string: str) -> str:
    """Форматировать дату и время для отображения"""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(dt_string)
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        return dt_string

def calculate_percentage(value: float, total: float) -> float:
    """Вычислить процент"""
    if total == 0:
        return 0.0
    return (value / total) * 100

def is_valid_username(username: str) -> bool:
    """Проверить валидность username Telegram"""
    if not username:
        return False
    
    # Username должен быть от 5 до 32 символов, начинаться с буквы
    # и содержать только буквы, цифры и подчеркивания
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$'
    return bool(re.match(pattern, username))

def format_large_number(number: int) -> str:
    """Форматировать большие числа (1000 -> 1K)"""
    if number >= 1000000:
        return f"{number/1000000:.1f}M"
    elif number >= 1000:
        return f"{number/1000:.1f}K"
    else:
        return str(number)

def generate_referral_link(bot_username: str, user_id: int) -> str:
    """Сгенерировать реферальную ссылку"""
    return f"https://t.me/{bot_username}?start=ref_{user_id}"

def parse_command_args(text: str) -> list:
    """Парсинг аргументов команды"""
    parts = text.split()[1:]  # Убираем саму команду
    return [part.strip() for part in parts if part.strip()]

def escape_html(text: str) -> str:
    """Экранировать HTML символы"""
    if not text:
        return ""
    
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    
    return text

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Обрезать текст до указанной длины"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
