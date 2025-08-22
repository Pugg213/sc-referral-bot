"""
Middleware для проверки подписки при каждом взаимодействии с ботом
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

from app.context import get_config, get_db
from app.utils.subscription import check_user_subscriptions
from app.keyboards import get_subscription_keyboard
from app.utils.helpers import format_user_mention

class SubscriptionGuardMiddleware(BaseMiddleware):
    """Middleware для постоянной проверки подписки пользователей"""
    
    def __init__(self):
        super().__init__()
        self.exempt_commands = {'/start', '/help', '/admin', '/stats'}
        self.exempt_callbacks = {'check_subscription'}
        self.admin_ids = {545921}  # Админы освобождены от проверок
        
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем только для обычных сообщений и callback'ов
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)
            
        # Получаем user_id
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            # Пропускаем exempt команды
            if event.text and any(event.text.startswith(cmd) for cmd in self.exempt_commands):
                return await handler(event, data)
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            # Пропускаем exempt callback'ы
            if event.data in self.exempt_callbacks:
                return await handler(event, data)
        
        if not user_id:
            return await handler(event, data)
        
        # Админы освобождены от всех проверок
        if user_id in self.admin_ids:
            return await handler(event, data)
            
        # Проверяем подписку для зарегистрированных пользователей
        db = get_db()
        user = db.get_user(user_id)
        
        if not user:
            # Пользователь не зарегистрирован - пропускаем
            return await handler(event, data)
            
        # Если пользователь уже прошел проверку подписки, делаем периодическую проверку
        if user.get('subscription_checked'):
            cfg = get_config()
            bot = data.get('bot')
            
            if bot:
                try:
                    # Быстрая проверка подписки
                    is_still_subscribed = await check_user_subscriptions(
                        bot, user_id, cfg.REQUIRED_CHANNEL_ID, cfg.REQUIRED_GROUP_ID
                    )
                    
                    if not is_still_subscribed:
                        # Пользователь отписался! Блокируем доступ
                        logging.warning(f"User {user_id} unsubscribed - blocking access")
                        
                        # Обновляем статус в БД
                        db.update_subscription_status(user_id, False)
                        
                        # Отправляем уведомление
                        keyboard = get_subscription_keyboard(cfg.CHANNEL_LINK, cfg.GROUP_LINK)
                        unsubscribe_text = (
                            "⚠️ <b>Доступ заблокирован!</b>\n\n"
                            "❌ Вы отписались от обязательного канала Simple Coin\n\n"
                            "📋 <b>Для восстановления доступа подпишитесь:</b>\n"
                            f"🔗 <a href='{cfg.CHANNEL_LINK}'>📢 Канал Simple Coin</a>\n\n"
                            "💡 <i>После подписки нажмите кнопку \"Проверить подписку\"</i>"
                        )
                        
                        if isinstance(event, Message):
                            await event.answer(unsubscribe_text, reply_markup=keyboard)
                        elif isinstance(event, CallbackQuery):
                            await event.answer("❌ Доступ заблокирован - подпишитесь на канал!", show_alert=True)
                            try:
                                if event.message and hasattr(event.message, 'edit_text'):
                                    await event.message.edit_text(unsubscribe_text, reply_markup=keyboard)
                            except Exception:
                                pass  # Message might be inaccessible
                        
                        # Прерываем выполнение основного handler'а
                        return
                        
                except Exception as e:
                    # Если не можем проверить - пропускаем (возможна временная ошибка API)
                    logging.warning(f"Subscription check failed for user {user_id}: {e}")
        
        # Пользователь подписан или проверка не удалась - продолжаем
        return await handler(event, data)