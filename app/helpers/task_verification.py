"""
Модуль для проверки выполнения заданий
"""
import logging
from typing import Optional, Tuple
from aiogram import Bot

async def verify_subscription(bot: Bot, user_id: int, target_url: str, task_type: str) -> Tuple[bool, Optional[str]]:
    """
    Проверить выполнение задания пользователем
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        target_url: URL канала/группы
        task_type: Тип задания ('channel_subscription' или 'group_join')
    
    Returns:
        Tuple[bool, Optional[str]]: (успех, сообщение об ошибке)
    """
    
    # Извлечь username из URL
    username = extract_username_from_url(target_url)
    
    if not username:
        # Не можем проверить - принимаем на честность
        return True, None
    
    try:
        # Получить информацию о пользователе в чате
        member = await bot.get_chat_member(f"@{username}", user_id)
        
        # Проверить статус участника
        if member.status in ['member', 'administrator', 'creator']:
            return True, None
        elif member.status == 'left':
            return False, f"Вы не подписаны на @{username}"
        elif member.status == 'kicked':
            return False, f"Вы заблокированы в @{username}"
        else:
            return False, f"Неизвестный статус в @{username}"
            
    except Exception as e:
        error_str = str(e).lower()
        
        if "chat not found" in error_str:
            # Канал не найден - возможно приватный или неверная ссылка
            logging.warning(f"Chat not found for {username}: {e}")
            return True, None  # Принимаем на честность
            
        elif "forbidden" in error_str:
            # Бот не имеет доступа к каналу
            logging.warning(f"Bot forbidden in {username}: {e}")
            return True, None  # Принимаем на честность
            
        elif "user not found" in error_str:
            return False, "Пользователь не найден в системе Telegram"
            
        else:
            # Другие ошибки
            logging.error(f"Error checking subscription for {username}: {e}")
            return False, f"Ошибка проверки: {str(e)[:50]}"

def extract_username_from_url(url: str) -> Optional[str]:
    """
    Извлечь username канала/группы из URL
    
    Args:
        url: URL в формате t.me/username или https://t.me/username
        
    Returns:
        Optional[str]: username без @ или None если не удалось извлечь
    """
    if not url or not isinstance(url, str):
        return None
    
    # Очистить URL
    url = url.strip()
    
    # Поддерживаемые форматы:
    # https://t.me/username
    # http://t.me/username  
    # t.me/username
    # @username
    
    if 't.me/' in url:
        username = url.split('t.me/')[-1]
        # Убрать дополнительные параметры после /
        username = username.split('/')[0]
        # Убрать символ @
        username = username.replace('@', '')
        
        # Проверить что это не приватная ссылка (начинается с +)
        if username.startswith('+') or len(username) < 1:
            return None
            
        return username
        
    elif url.startswith('@'):
        username = url[1:]  # Убрать @
        if len(username) > 0 and not username.startswith('+'):
            return username
    
    return None

async def get_chat_info(bot: Bot, username: str) -> Optional[dict]:
    """
    Получить информацию о канале/группе
    
    Args:
        bot: Экземпляр бота
        username: Username канала/группы
        
    Returns:
        Optional[dict]: Информация о чате или None
    """
    try:
        chat = await bot.get_chat(f"@{username}")
        return {
            'id': chat.id,
            'title': chat.title,
            'type': chat.type,
            'username': chat.username,
            'description': chat.description,
            'member_count': getattr(chat, 'member_count', None)
        }
    except Exception as e:
        logging.error(f"Error getting chat info for {username}: {e}")
        return None

def is_valid_telegram_url(url: str) -> bool:
    """
    Проверить валидность Telegram URL
    
    Args:
        url: URL для проверки
        
    Returns:
        bool: True если URL валидный
    """
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip().lower()
    
    # Поддерживаемые форматы
    valid_prefixes = [
        'https://t.me/',
        'http://t.me/',
        't.me/',
        '@'
    ]
    
    return any(url.startswith(prefix) for prefix in valid_prefixes)