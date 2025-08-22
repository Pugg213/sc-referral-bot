"""
Утилиты для проверки подписки на каналы и группы
"""
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from app.utils.test_mode import is_test_mode, mock_subscription_check

async def check_user_subscriptions(bot: Bot, user_id: int, channel_id: str, group_id: str) -> bool:
    """Проверить подписку пользователя на канал и группу"""
    
    # Если включен тестовый режим, используем мок
    if is_test_mode():
        return await mock_subscription_check(bot, user_id, channel_id, group_id)
    
    # Проверить канал (обязательно)
    channel_subscribed = await check_channel_subscription(bot, user_id, channel_id)
    if not channel_subscribed:
        logging.info(f"User {user_id} not subscribed to channel {channel_id}")
        return False
    
    # Проверить конфигурацию на пропуск группы
    from app.context import get_config
    cfg = get_config()
    if getattr(cfg, 'SKIP_GROUP_CHECK', False):
        logging.info(f"Group check skipped for user {user_id} (SKIP_GROUP_CHECK=True)")
        return True
    
    # Проверить группу только если бот в ней участвует
    try:
        # Сначала проверим статус бота в группе
        bot_info = await bot.get_me()
        bot_member = await bot.get_chat_member(group_id, bot_info.id)
        
        if bot_member.status == "left":
            logging.warning(f"Bot is not in group {group_id}. Skipping group check for user {user_id}")
            # Пока группа недоступна, проверяем только канал
            return True
        
        group_subscribed = await check_group_membership(bot, user_id, group_id)
        if not group_subscribed:
            logging.info(f"User {user_id} not in group {group_id}")
            return False
    except Exception as e:
        logging.warning(f"Error checking group membership for user {user_id}: {e}")
        # Если не можем проверить группу, проверяем только канал
        return True
    
    logging.info(f"User {user_id} passed all subscription checks")
    return True

async def check_channel_subscription(bot: Bot, user_id: int, channel_id: str) -> bool:
    """Проверить подписку на канал с быстрым откликом"""
    try:
        # Используем таймаут для каждого API вызова
        import asyncio
        member = await asyncio.wait_for(
            bot.get_chat_member(channel_id, user_id),
            timeout=3.0
        )
        
        # Пользователь подписан, если он не покинул канал и не кикнут
        return member.status in ['member', 'administrator', 'creator']
        
    except TelegramBadRequest as e:
        if "user not found" in str(e).lower():
            logging.warning(f"User {user_id} not found in channel {channel_id}")
            return False
        logging.error(f"Error checking channel subscription: {e}")
        return False
    except TelegramForbiddenError:
        logging.error(f"Bot has no access to channel {channel_id}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error checking channel subscription: {e}")
        return False

async def check_group_membership(bot: Bot, user_id: int, group_id: str) -> bool:
    """Проверить участие в группе с быстрым откликом"""
    try:
        # Используем таймаут для API вызова группы
        import asyncio
        member = await asyncio.wait_for(
            bot.get_chat_member(group_id, user_id),
            timeout=3.0
        )
        
        # Пользователь участвует, если он не покинул группу и не кикнут
        return member.status in ['member', 'administrator', 'creator']
        
    except TelegramBadRequest as e:
        if "user not found" in str(e).lower():
            logging.warning(f"User {user_id} not found in group {group_id}")
            return False
        logging.error(f"Error checking group membership: {e}")
        return False
    except TelegramForbiddenError:
        logging.error(f"Bot has no access to group {group_id}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error checking group membership: {e}")
        return False

async def get_chat_info(bot: Bot, chat_id: str) -> dict:
    """Получить информацию о чате"""
    try:
        chat = await bot.get_chat(chat_id)
        return {
            'id': chat.id,
            'title': chat.title,
            'type': chat.type,
            'username': chat.username,
            'description': chat.description
        }
    except Exception as e:
        logging.error(f"Error getting chat info for {chat_id}: {e}")
        return {}

async def check_bot_permissions(bot: Bot, chat_id: str) -> dict:
    """Проверить права бота в чате"""
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        
        permissions = {
            'is_admin': bot_member.status in ['administrator', 'creator'],
            'can_invite_users': getattr(bot_member, 'can_invite_users', False),
            'can_delete_messages': getattr(bot_member, 'can_delete_messages', False),
            'can_restrict_members': getattr(bot_member, 'can_restrict_members', False)
        }
        
        return permissions
        
    except Exception as e:
        logging.error(f"Error checking bot permissions in {chat_id}: {e}")
        return {
            'is_admin': False,
            'can_invite_users': False,
            'can_delete_messages': False,
            'can_restrict_members': False
        }
