"""
Универсальные обработчики для всех кнопок и callback - гарантирует 100% покрытие
"""
import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery

from app.context import get_config, get_db
from app.keyboards import (
    get_main_keyboard, get_profile_keyboard, 
    get_wallet_keyboard, get_referrals_keyboard
)
from app.utils.helpers import format_balance, format_user_mention

router = Router()

@router.message(F.text == "👥 Рефералы")
@router.callback_query(F.data == "referrals")
async def referrals_handler(message_or_callback):
    """Показать информацию о рефералах"""
    if hasattr(message_or_callback, 'from_user') and hasattr(message_or_callback, 'answer'):
        # Это message
        user = message_or_callback.from_user
        message = message_or_callback
        callback = None
    else:
        # Это callback
        user = message_or_callback.from_user
        message = message_or_callback.message
        callback = message_or_callback
        
    if not user:
        return
    
    user_id = user.id
    db = get_db()
    
    user_data = db.get_user(user_id)
    if not user_data:
        text = "❌ Вы не зарегистрированы. Используйте /start"
        if callback:
            await callback.answer(text, show_alert=True)
        else:
            await message.answer(text)
        return
    
    # Получаем бота для генерации ссылки
    bot = message.bot if message else message_or_callback.bot
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    referrals_text = (
        f"👥 <b>Ваши рефералы</b>\n\n"
        f"📝 Всего приглашено: {user_data['total_referrals']}\n"
        f"✅ Подтверждено: {user_data['validated_referrals']}\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"💡 Поделитесь ссылкой с друзьями и получайте:"
        f"• Дополнительные капсулы за каждого реферала\n"
        f"• Бонусы за активных пользователей"
    )
    
    if callback:
        await callback.message.edit_text(referrals_text, reply_markup=get_referrals_keyboard())
        await callback.answer()
    else:
        await message.answer(referrals_text, reply_markup=get_referrals_keyboard())

@router.message(F.text == "💼 Кошелек")
@router.callback_query(F.data == "wallet")
async def wallet_handler(message_or_callback):
    """Показать информацию о кошельке"""
    if hasattr(message_or_callback, 'from_user') and hasattr(message_or_callback, 'answer'):
        # Это message
        user = message_or_callback.from_user
        message = message_or_callback
        callback = None
    else:
        # Это callback
        user = message_or_callback.from_user
        message = message_or_callback.message
        callback = message_or_callback
        
    if not user:
        return
    
    user_id = user.id
    db = get_db()
    
    user_data = db.get_user(user_id)
    if not user_data:
        text = "❌ Вы не зарегистрированы. Используйте /start"
        if callback:
            await callback.answer(text, show_alert=True)
        else:
            await message.answer(text)
        return
    
    wallet_info = user_data['wallet_address'] if user_data['wallet_address'] else "Не указан"
    
    wallet_text = (
        f"💼 <b>Ваш кошелек</b>\n\n"
        f"💰 <b>Баланс SC:</b>\n"
        f"💳 Доступно: {format_balance(user_data['pending_balance'])}\n"
        f"✅ Выплачено: {format_balance(user_data['paid_balance'])}\n"
        f"📈 Всего заработано: {format_balance(user_data['total_earnings'])}\n\n"
        f"💼 <b>TON кошелек:</b> <code>{wallet_info}</code>\n\n"
        f"💡 Привяжите кошелек TON для получения выплат"
    )
    
    if callback:
        await callback.message.edit_text(wallet_text, reply_markup=get_wallet_keyboard())
        await callback.answer()
    else:
        await message.answer(wallet_text, reply_markup=get_wallet_keyboard())

@router.message(F.text == "🏆 Топ")
@router.callback_query(F.data == "leaderboard")
async def leaderboard_handler(message_or_callback):
    """Показать топ пользователей"""
    if hasattr(message_or_callback, 'from_user') and hasattr(message_or_callback, 'answer'):
        callback = None
        message = message_or_callback
    else:
        callback = message_or_callback
        message = message_or_callback.message
        
    db = get_db()
    
    # Получаем топ пользователей
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT first_name, username, total_earnings, total_referrals, total_capsules_opened
            FROM users 
            WHERE subscription_checked = 1 AND banned = 0
            ORDER BY total_earnings DESC 
            LIMIT 10
        """)
        top_users = cursor.fetchall()
    
    if not top_users:
        top_text = "🏆 <b>Топ пользователей</b>\n\nПока никого нет в рейтинге!"
    else:
        top_text = "🏆 <b>Топ пользователей</b>\n\n"
        for i, user in enumerate(top_users, 1):
            first_name, username, earnings, referrals, capsules = user
            user_mention = format_user_mention(first_name, username)
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            top_text += f"{medal} {user_mention} - {format_balance(earnings)} SC\n"
    
    if callback:
        await callback.message.edit_text(top_text)
        await callback.answer()
    else:
        await message.answer(top_text)

@router.message(F.text == "🎯 Задания")
@router.callback_query(F.data == "tasks")
async def tasks_handler(message_or_callback):
    """Показать доступные задания"""
    if hasattr(message_or_callback, 'from_user') and hasattr(message_or_callback, 'answer'):
        callback = None
        message = message_or_callback
    else:
        callback = message_or_callback
        message = message_or_callback.message
        
    db = get_db()
    
    # Получаем активные задания
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title, description, reward_capsules, partner_name 
            FROM tasks 
            WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        tasks = cursor.fetchall()
    
    if not tasks:
        tasks_text = "🎯 <b>Задания</b>\n\nПока нет доступных заданий!"
    else:
        tasks_text = "🎯 <b>Доступные задания</b>\n\n"
        for title, description, reward, partner in tasks:
            tasks_text += f"📋 <b>{title}</b>\n"
            tasks_text += f"💼 Партнер: {partner or 'SC Team'}\n"
            tasks_text += f"🎁 Награда: {reward} капсул\n"
            tasks_text += f"📝 {description}\n\n"
    
    if callback:
        await callback.message.edit_text(tasks_text)
        await callback.answer()
    else:
        await message.answer(tasks_text)

@router.message(F.text == "📋 Правила")
@router.callback_query(F.data == "rules")
async def rules_handler(message_or_callback):
    """Показать правила бота"""
    if hasattr(message_or_callback, 'from_user') and hasattr(message_or_callback, 'answer'):
        callback = None
        message = message_or_callback
    else:
        callback = message_or_callback
        message = message_or_callback.message
        
    rules_text = (
        f"📋 <b>Правила бота SC Referral</b>\n\n"
        f"✅ <b>Разрешено:</b>\n"
        f"• Честное участие в реферальной программе\n"
        f"• Приглашение реальных людей\n"
        f"• Открытие капсул согласно лимитам\n"
        f"• Выполнение партнерских заданий\n\n"
        f"❌ <b>Запрещено:</b>\n"
        f"• Использование ботов и накрутки\n"
        f"• Создание фейковых аккаунтов\n"
        f"• Спам и злоупотребления\n"
        f"• Попытки обмана системы\n\n"
        f"⚖️ <b>Наказания:</b>\n"
        f"• Предупреждение\n"
        f"• Временная блокировка\n"
        f"• Полная блокировка аккаунта\n\n"
        f"💎 <b>Награды:</b>\n"
        f"• 0.5 - 10 SC токенов за капсулу\n"
        f"• Бонусные капсулы за рефералов\n"
        f"• Специальные задания партнеров"
    )
    
    if callback:
        await callback.message.edit_text(rules_text)
        await callback.answer()
    else:
        await message.answer(rules_text)