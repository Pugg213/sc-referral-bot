"""
Тестовый режим для отладки без реальных каналов
"""
import os
import logging

def is_test_mode() -> bool:
    """Проверить, включен ли тестовый режим"""
    return os.getenv("TEST_MODE", "false").lower() == "true"

async def mock_subscription_check(bot, user_id: int, channel_id: str, group_id: str) -> bool:
    """Имитация проверки подписки для тестирования"""
    if not is_test_mode():
        return False
    
    logging.info(f"TEST MODE: Mock subscription check for user {user_id}")
    print(f"🧪 ТЕСТОВЫЙ РЕЖИМ: Имитация проверки подписки для пользователя {user_id}")
    print(f"   Канал: {channel_id}")
    print(f"   Группа: {group_id}")
    
    # В тестовом режиме всегда возвращаем True
    return True