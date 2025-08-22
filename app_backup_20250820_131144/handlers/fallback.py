"""
Fallback обработчики для необработанных обновлений
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.enums import ChatType

router = Router()

@router.callback_query()
async def fallback_callback(callback: types.CallbackQuery):
    """Обработчик для всех необработанных callback"""
    logging.warning(f"Unhandled callback: {callback.data} from user {callback.from_user.id if callback.from_user else 'None'}")
    
    if callback.data:
        if callback.data.startswith("main_menu") or callback.data.startswith("back"):
            await callback.answer("🏠 Используйте кнопки главного меню")
        elif callback.data.startswith("open_capsule"):
            await callback.answer("🎁 Используйте кнопку 'Открыть капсулу' в главном меню")
        elif callback.data.startswith("profile") or callback.data.startswith("wallet"):
            await callback.answer("👤 Используйте кнопки профиля в главном меню")
        else:
            await callback.answer("ℹ️ Функция временно недоступна")
    else:
        await callback.answer("❓ Неизвестная команда")

@router.message(F.chat.type == ChatType.PRIVATE)
async def fallback_message(message: types.Message):
    """Обработчик для всех необработанных сообщений - только для команд в приватных чатах"""
    if not message.from_user:
        return
        
    text = message.text or ""
    user_id = message.from_user.id
    
    # Отвечаем только на команды, игнорируем обычные сообщения
    if text.startswith('/'):
        logging.warning(f"Unhandled command: '{text}' from user {user_id}")
        await message.answer(
            "❓ Неизвестная команда.\n\n"
            "Доступные команды:\n"
            "/start - начать работу\n"
            "/check - проверить подписку\n" 
            "/wallet <адрес> - привязать кошелек"
        )
    else:
        # Просто логируем обычные сообщения, но НЕ отвечаем на них
        logging.info(f"Regular message ignored: '{text}' from user {user_id}")
        # НЕ отправляем навигационное сообщение!

# Специальный обработчик для групп - полностью игнорирует все сообщения
@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def group_message_handler(message: types.Message):
    """Игнорируем все сообщения в группах"""
    # Просто логируем что получили сообщение в группе, но НЕ отвечаем
    if message.from_user:
        logging.info(f"Group message ignored from user {message.from_user.id} in chat {message.chat.id}")
    # Полностью игнорируем - никаких ответов