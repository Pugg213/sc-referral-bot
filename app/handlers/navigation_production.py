"""
Финальные навигационные хендлеры БЕЗ LSP ошибок для ПРОДАКШНА
"""
import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType

from app.context import get_config, get_db
from app.keyboards import get_main_keyboard
from datetime import date
from app.utils.helpers import format_balance

router = Router()

# TEXT MESSAGE HANDLERS - для Reply клавиатуры

# ПРОФИЛЬ HANDLER - КРИТИЧНО ВАЖНЫЙ  
@router.message(F.text == "👤 Профиль", F.chat.type == ChatType.PRIVATE)
async def profile_text_handler(message: Message):
    """Обработчик текста 'Профиль' """
    try:
        if not message.from_user:
            return
            
        user_id = message.from_user.id
        db = get_db()
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start")
            return
        
        # Получаем конфиг
        cfg = get_config()
        daily_limit = cfg.DAILY_CAPSULE_LIMIT if cfg else 3
        
        profile_text = f"""👤 <b>Ваш профиль</b>

🆔 <b>ID:</b> <code>{user['user_id']}</code>
👋 <b>Имя:</b> {user['first_name'] or 'Не указано'}
📅 <b>Регистрация:</b> {user['registration_date'][:10] if user['registration_date'] else 'Недавно'}

💰 <b>Баланс SC:</b>
💳 Доступно: {format_balance(user['balance'])} SC
✅ Выплачено: {format_balance(user['paid_balance'])} SC  
📈 Всего заработано: {format_balance(user['total_earnings'])} SC

👥 <b>Рефералы:</b>
🔗 Приглашено: {user.get('total_referrals', 0) or 0}
✅ Активных: {user.get('validated_referrals', 0) or 0}

🎁 <b>Капсулы:</b>
📦 Открыто сегодня: {user['daily_capsules_opened']}
🎯 Дневной лимит: {daily_limit + (user.get('validated_referrals', 0) or 0)}
📊 Всего открыто: {user['total_capsules_opened'] or 0}"""
        
        # Inline кнопки для профиля
        keyboard_buttons = [
            [InlineKeyboardButton(text="🎁 Открыть капсулу", callback_data="open_capsule")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"), InlineKeyboardButton(text="💼 Кошелек", callback_data="wallet")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(profile_text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Profile handler error: {e}")
        try:
            await message.answer("❌ Ошибка загрузки профиля")
        except Exception as e2:
            logging.error(f"Profile fallback failed: {e2}")

# КАПСУЛЫ HANDLER - КРИТИЧНО ВАЖНЫЙ
@router.message(F.text == "🎁 Открыть капсулу", F.chat.type == ChatType.PRIVATE)
async def capsule_text_handler(message: Message):
    """Обработчик текста 'Открыть капсулу' """
    try:
        if not message.from_user:
            return
            
        user_id = message.from_user.id
        db = get_db()
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start")
            return
        
        # Проверяем доступные капсулы правильно (с учетом бонусов)
        from app.services.special_rewards import SpecialRewardService
        special_service = SpecialRewardService()
        available_capsules = special_service.get_available_capsules(user_id)
        
        if available_capsules <= 0:
            cfg = get_config()
            referral_bonus = user['validated_referrals'] if user['validated_referrals'] else 0
            bonus_capsules = user.get('bonus_capsules', 0) or 0
            
            limit_text = (
                f"📦 Лимит капсул исчерпан!\n\n"
                f"💡 Ваш лимит:\n"
                f"• {cfg.DAILY_CAPSULE_LIMIT} базовых капсул\n"
                f"• +{referral_bonus} за рефералов\n"
                f"• +{bonus_capsules} бонусных\n\n"
                f"⏰ Попробуйте завтра или пригласите больше друзей!"
            )
            await message.answer(limit_text)
            return
            
        # ИСПОЛЬЗУЕМ ПРАВИЛЬНУЮ СИСТЕМУ КАПСУЛ
        from app.services.capsules import CapsuleService
        from app.services.special_rewards import SpecialRewardService
        cfg = get_config()
        
        capsule_service = CapsuleService()
        special_service = SpecialRewardService()
        
        # Получить награду через правильную систему
        reward_obj = capsule_service.open_capsule(cfg.CAPSULE_REWARDS)
        if not reward_obj:
            await message.answer("❌ Ошибка открытия капсулы")
            return
            
        # Обработать специальную награду
        reward_result = special_service.process_special_reward(user_id, reward_obj.name, reward_obj.amount)
        
        # Обновить статистику капсул
        db.update_user_capsule_stats(user_id, reward_obj.amount)
        
        # Записать в историю
        db.record_capsule_opening(user_id, reward_obj.name, reward_obj.amount)
        
        # Правильный расчет лимита
        total_limit = cfg.DAILY_CAPSULE_LIMIT + (user.get('validated_referrals', 0) or 0) + (user.get('bonus_capsules', 0) or 0)
        
        # Обновленные данные пользователя
        updated_user = db.get_user(user_id)
        
        # Безопасное отображение результата
        emoji = reward_result.get('emoji', '🎁') if reward_result else '🎁'
        message = reward_result.get('message', f"Награда: {reward_obj.amount} SC") if reward_result else f"Награда: {reward_obj.amount} SC"
        
        capsule_text = f"""🎁 <b>Капсула открыта!</b>

{emoji} {message}
📦 Открыто сегодня: {updated_user['daily_capsules_opened']}/{total_limit}
💳 Баланс: {format_balance(updated_user['balance'])} SC"""
        
        # Кнопки после открытия
        keyboard_buttons = [
            [InlineKeyboardButton(text="🎁 Открыть еще", callback_data="open_capsule")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"), InlineKeyboardButton(text="💼 Кошелек", callback_data="wallet")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(capsule_text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Capsule handler error: {e}")
        await message.answer("❌ Ошибка открытия капсулы")

# РЕФЕРАЛЫ HANDLER - КРИТИЧНО ВАЖНЫЙ
@router.message(F.text == "👥 Рефералы", F.chat.type == ChatType.PRIVATE)
async def referrals_text_handler(message: Message):
    """Обработчик текста 'Рефералы' """
    try:
        if not message.from_user:
            return
            
        user_id = message.from_user.id  
        db = get_db()
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start")
            return
        
        referrals_text = f"""👥 <b>Ваши рефералы</b>

🔗 <b>Ваша реферальная ссылка:</b>
<code>https://t.me/scReferalbot?start={user_id}</code>

📊 <b>Статистика:</b>
👤 Приглашено: {user.get('total_referrals', 0) or 0}
✅ Активных: {user.get('validated_referrals', 0) or 0}
💰 Общий заработок: {format_balance(user.get('total_earnings', 0) or 0)} SC

🎁 <b>Бонусы:</b>
• +1 капсула в день за каждого активного реферала
• 10% от заработка рефералов
• Специальные задания для активных пригласителей

💡 <b>Как работает:</b>
1. Поделитесь вашей ссылкой
2. Новый пользователь регистрируется
3. После подтверждения подписки - вы получаете бонусы"""
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="📊 Статистика рефералов", callback_data="referral_stats")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(referrals_text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Referrals handler error: {e}")
        await message.answer("❌ Ошибка загрузки рефералов")

# ТОП HANDLER - КРИТИЧНО ВАЖНЫЙ
@router.message(F.text == "🏆 Топ", F.chat.type == ChatType.PRIVATE)
async def top_text_handler(message: Message):
    """Обработчик текста 'Топ' """
    try:
        if not message.from_user:
            return
            
        user_id = message.from_user.id
        db = get_db()
        
        # Получаем топ пользователей
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT first_name, total_earnings, validated_referrals, user_id
                FROM users 
                WHERE total_earnings > 0
                ORDER BY total_earnings DESC
                LIMIT 10
            """)
            top_users = cursor.fetchall()
            
            # Получаем позицию текущего пользователя
            cursor.execute("""
                SELECT COUNT(*) + 1 as position
                FROM users
                WHERE total_earnings > (
                    SELECT total_earnings FROM users WHERE user_id = ?
                )
            """, (user_id,))
            user_position = cursor.fetchone()[0]
        
        top_text = "🏆 <b>Топ пользователей</b>\n\n"
        
        if top_users:
            for i, (name, earnings, refs, uid) in enumerate(top_users, 1):
                icon = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                name_display = name or "Анонимный"
                if len(name_display) > 15:
                    name_display = name_display[:15] + "..."
                
                top_text += f"{icon} <b>{name_display}</b>\n"
                top_text += f"    💰 {format_balance(earnings)} SC | 👥 {refs or 0} ref\n\n"
        else:
            top_text += "Пока нет данных\n\n"
            
        top_text += f"📊 <b>Ваша позиция:</b> #{user_position}"
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(top_text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Top handler error: {e}")
        await message.answer("❌ Ошибка загрузки рейтинга")

# КОШЕЛЕК HANDLER - КРИТИЧНО ВАЖНЫЙ
@router.message(F.text == "💼 Кошелек", F.chat.type == ChatType.PRIVATE)
async def wallet_text_handler(message: Message):
    """Обработчик текста 'Кошелек' """
    try:
        if not message.from_user:
            return
            
        user_id = message.from_user.id
        db = get_db()
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start")
            return
            
        # Безопасно получаем конфиг
        cfg = get_config()
        daily_limit = cfg.DAILY_CAPSULE_LIMIT if cfg else 3
        
        wallet_text = f"""💼 <b>Ваш кошелек</b>

💰 <b>Баланс SC:</b>
💳 Доступно: {format_balance(user['balance'])} SC
✅ Выплачено: {format_balance(user['paid_balance'])} SC
📈 Всего заработано: {format_balance(user['total_earnings'])} SC

🏦 <b>TON Кошелек:</b>
📱 Адрес: {user['wallet_address'] if user['wallet_address'] else 'Не подключен'}

🎁 <b>Капсулы сегодня:</b>
📦 Открыто: {user['daily_capsules_opened']}
🎯 Лимит: {daily_limit + (user['validated_referrals'] or 0)}

💡 <b>Управление кошельком:</b>
/wallet - изменить адрес кошелька
/withdraw - запросить вывод средств"""
        
        # Inline кнопки для кошелька
        keyboard_buttons = [
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(wallet_text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Wallet handler error: {e}")
        await message.answer("❌ Ошибка загрузки кошелька")

# КОШЕЛЕК CALLBACK HANDLER - КРИТИЧНО ВАЖНЫЙ для Inline кнопок
@router.callback_query(F.data == "wallet")
async def wallet_callback_handler(callback: CallbackQuery):
    """Обработчик callback 'wallet' для Inline кнопок"""
    try:
        if not callback.from_user or not callback.message:
            return
            
        user_id = callback.from_user.id
        db = get_db()
        user = db.get_user(user_id)
        
        if not user:
            await callback.answer("❌ Вы не зарегистрированы. Используйте /start", show_alert=True)
            return
            
        # Безопасно получаем конфиг
        cfg = get_config()
        daily_limit = cfg.DAILY_CAPSULE_LIMIT if cfg else 3
        
        wallet_text = f"""💼 <b>Ваш кошелек</b>

💰 <b>Баланс SC:</b>
💳 Доступно: {format_balance(user['balance'])} SC
✅ Выплачено: {format_balance(user['paid_balance'])} SC
📈 Всего заработано: {format_balance(user['total_earnings'])} SC

🏦 <b>TON Кошелек:</b>
📱 Адрес: {user['wallet_address'] if user['wallet_address'] else 'Не подключен'}

🎁 <b>Капсулы сегодня:</b>
📦 Открыто: {user['daily_capsules_opened']}
🎯 Лимит: {daily_limit + (user['validated_referrals'] or 0)}

💡 <b>Управление кошельком:</b>
/wallet - изменить адрес кошелька
/withdraw - запросить вывод средств"""
        
        # Inline кнопки для кошелька
        keyboard_buttons = [
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Отправляем новое сообщение
        if callback.message:
            await callback.message.answer(wallet_text, reply_markup=keyboard, parse_mode="HTML")
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Wallet callback error: {e}")
        await callback.answer("❌ Ошибка загрузки кошелька", show_alert=True)

@router.message(F.text == "📋 Правила", F.chat.type == ChatType.PRIVATE)
async def rules_text_handler(message: Message):
    """Обработчик текста 'Правила' """
    try:
        rules_text = """📋 <b>Правила использования бота</b>

🔸 <b>Основные правила:</b>
• Подпишитесь на канал и войдите в группу
• Не создавайте фейковые аккаунты
• Приглашайте только реальных пользователей
• Не спамьте и не нарушайте правила Telegram

🎁 <b>Система капсул:</b>
• 3 капсулы в день базово
• +1 капсула за каждого активного реферала
• Бонусные капсулы за выполнение заданий

💰 <b>Награды:</b>
• 0.5-10 SC токенов за капсулу
• Бонусы за активность рефералов
• Специальные задания от партнеров

⚠️ <b>Ограничения:</b>
• Новые аккаунты проходят карантин 1 час
• Подозрительная активность блокируется
• Нарушители исключаются из программы

🔗 <b>Полезные ссылки:</b>
• Канал: https://t.me/just_a_simple_coin
• Чат: https://t.me/simplecoin_chatSC"""
        
        await message.answer(rules_text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Rules text error: {e}")
        await message.answer("❌ Ошибка загрузки правил")

@router.message(F.text == "🎯 Задания", F.chat.type == ChatType.PRIVATE)
async def tasks_text_handler(message: Message):
    """Обработчик текста 'Задания' - перенаправляем к реальной системе заданий"""
    from app.handlers.tasks_unified import tasks_menu
    try:
        # Перенаправляем к полноценной системе заданий
        await tasks_menu(message)
    except Exception as e:
        logging.error(f"Tasks redirect error: {e}")
        await message.answer("❌ Ошибка загрузки заданий")

# CALLBACK HANDLERS - упрощенные БЕЗ LSP ошибок
@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Главное меню"""
    try:
        text = "🏠 <b>Главное меню</b>\n\nИспользуйте кнопки для навигации:"
        await callback.answer()
        if callback.message:
            await callback.message.answer(text, reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Main menu error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    """Назад в меню"""
    try:
        text = "🏠 <b>Главное меню</b>\n\nВыберите действие:"
        await callback.answer()
        if callback.message:
            await callback.message.answer(text, reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Back to menu error: {e}")
        await callback.answer("❌ Ошибка")

@router.message(F.text == "📅 Чек-ин")
async def checkin_button(message: types.Message):
    """Обработка кнопки ежедневного чек-ина"""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    db = get_db()
    
    # Проверяем статус пользователя
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT subscription_checked, pending_balance 
            FROM users WHERE user_id = ?
        """, (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await message.answer("❌ Сначала зарегистрируйтесь в боте с помощью команды /start")
            return
        
        if not user_data[0]:
            await message.answer("❌ Сначала подтвердите подписку на канал")
            return
        
        # Проверяем чек-ин сегодня
        today = date.today().isoformat()
        cursor.execute("""
            SELECT id FROM user_checkins 
            WHERE user_id = ? AND checkin_date = ?
        """, (user_id, today))
        
        existing_checkin = cursor.fetchone()
        if existing_checkin:
            await message.answer("❌ Вы уже делали чек-ин сегодня! Возвращайтесь завтра.")
            return
        
        # Выполняем чек-ин
        checkin_reward = 0.5
        try:
            # Добавляем чек-ин
            cursor.execute("""
                INSERT INTO user_checkins (user_id, checkin_date, sc_amount)
                VALUES (?, ?, ?)
            """, (user_id, today, checkin_reward))
            
            # Обновляем баланс
            cursor.execute("""
                UPDATE users 
                SET pending_balance = pending_balance + ?,
                    total_earnings = total_earnings + ?
                WHERE user_id = ?
            """, (checkin_reward, checkin_reward, user_id))
            
            conn.commit()
            
            # Получаем общее количество чек-инов
            cursor.execute("""
                SELECT COUNT(*) FROM user_checkins WHERE user_id = ?
            """, (user_id,))
            total_checkins = cursor.fetchone()[0]
            
            # Получаем новый баланс
            new_balance = user_data[1] + checkin_reward
            
            success_text = (
                f"✅ <b>Ежедневный чек-ин выполнен!</b>\n\n"
                f"🎁 Получено: {format_balance(checkin_reward)} SC\n"
                f"💰 Ваш баланс: {format_balance(new_balance)} SC\n"
                f"📅 Всего чек-инов: {total_checkins}\n\n"
                f"💡 Возвращайтесь завтра за новой наградой!"
            )
            
            await message.answer(success_text)
            
        except Exception as e:
            logging.error(f"Checkin execution error for user {user_id}: {e}")
            await message.answer("❌ Ошибка выполнения чек-ина. Попробуйте позже.")

@router.callback_query(F.data == "daily_checkin")
async def daily_checkin_callback(callback: types.CallbackQuery):
    """Выполнение ежедневного чек-ина через callback"""
    if not callback.from_user:
        await callback.answer("❌ Ошибка системы", show_alert=True)
        return
    
    user_id = callback.from_user.id
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем чек-ин сегодня
            today = date.today().isoformat()
            cursor.execute("""
                SELECT id FROM user_checkins 
                WHERE user_id = ? AND checkin_date = ?
            """, (user_id, today))
            
            existing_checkin = cursor.fetchone()
            if existing_checkin:
                await callback.answer("❌ Чек-ин уже выполнен сегодня!", show_alert=True)
                return
            
            # Получаем данные пользователя
            cursor.execute("""
                SELECT subscription_checked, pending_balance, total_earnings
                FROM users WHERE user_id = ?
            """, (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data or not user_data[0]:
                await callback.answer("❌ Подтвердите подписку на канал", show_alert=True)
                return
            
            # Выполняем чек-ин
            checkin_reward = 0.5
            
            # Добавляем чек-ин
            cursor.execute("""
                INSERT INTO user_checkins (user_id, checkin_date, sc_amount)
                VALUES (?, ?, ?)
            """, (user_id, today, checkin_reward))
            
            # Обновляем баланс
            cursor.execute("""
                UPDATE users 
                SET pending_balance = pending_balance + ?,
                    total_earnings = total_earnings + ?
                WHERE user_id = ?
            """, (checkin_reward, checkin_reward, user_id))
            
            conn.commit()
            
            # Получаем общее количество чек-инов
            cursor.execute("""
                SELECT COUNT(*) FROM user_checkins WHERE user_id = ?
            """, (user_id,))
            total_checkins = cursor.fetchone()[0]
            
            # Получаем новый баланс
            new_balance = user_data[1] + checkin_reward
            
            success_text = (
                f"✅ <b>Ежедневный чек-ин выполнен!</b>\n\n"
                f"🎁 Получено: {format_balance(checkin_reward)} SC\n"
                f"💰 Ваш баланс: {format_balance(new_balance)} SC\n"
                f"📅 Всего чек-инов: {total_checkins}\n\n"
                f"💡 Возвращайтесь завтра за новой наградой!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            # Отправляем новое сообщение
            if callback.message:
                await callback.message.answer(success_text, reply_markup=keyboard, parse_mode="HTML")
            
            await callback.answer("🎉 Чек-ин выполнен! +0.5 SC")
            
    except Exception as e:
        logging.error(f"Daily checkin error for user {user_id}: {e}")
        await callback.answer("❌ Ошибка выполнения чек-ина", show_alert=True)

@router.callback_query(F.data == "checkin_stats")
async def checkin_stats_callback(callback: types.CallbackQuery):
    """Показать статистику чек-инов пользователя"""
    if not callback.from_user:
        await callback.answer("❌ Ошибка системы", show_alert=True)
        return
    
    user_id = callback.from_user.id
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем статистику пользователя
            cursor.execute("""
                SELECT COUNT(*), SUM(sc_amount), MAX(checkin_date)
                FROM user_checkins WHERE user_id = ?
            """, (user_id,))
            stats = cursor.fetchone()
            
            total_checkins = stats[0] if stats[0] else 0
            total_earned = stats[1] if stats[1] else 0
            last_checkin = stats[2] if stats[2] else "Никогда"
            
            # Проверяем чек-ин сегодня
            today = date.today().isoformat()
            cursor.execute("""
                SELECT id FROM user_checkins 
                WHERE user_id = ? AND checkin_date = ?
            """, (user_id, today))
            
            today_checkin = cursor.fetchone() is not None
            
            stats_text = (
                f"📊 <b>Статистика чек-инов</b>\n\n"
                f"📅 Всего чек-инов: {total_checkins}\n"
                f"🎁 Заработано: {format_balance(total_earned)} SC\n"
                f"📆 Последний чек-ин: {last_checkin}\n"
                f"✅ Сегодня: {'Выполнен' if today_checkin else 'Доступен'}\n\n"
                f"💡 Ежедневный чек-ин дает 0.5 SC!"
            )
            
            keyboard_buttons = []
            
            if not today_checkin:
                keyboard_buttons.append([InlineKeyboardButton(text="🎯 Сделать чек-ин", callback_data="daily_checkin")])
            
            keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            # Отправляем новое сообщение
            if callback.message:
                await callback.message.answer(stats_text, reply_markup=keyboard, parse_mode="HTML")
            
            await callback.answer()
            
    except Exception as e:
        logging.error(f"Checkin stats error for user {user_id}: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)

# ===============================
# КРИТИЧНЫЕ ОБРАБОТЧИКИ КНОПОК
# БЕЗ НИХ КНОПКИ НЕ РАБОТАЮТ!
# ===============================

@router.callback_query(F.data == "profile")
async def callback_profile(callback: CallbackQuery):
    """Профиль пользователя"""
    try:
        await callback.answer()
        if callback.message and callback.from_user:
            # Вызываем функцию профиля из текстового обработчика
            await profile_text_handler(callback.message)
    except Exception as e:
        logging.error(f"Profile callback error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "open_capsule")
async def callback_open_capsule(callback: CallbackQuery):
    """Открыть капсулу"""
    try:
        await callback.answer()
        if callback.message and callback.from_user:
            # Перенаправляем на текстовый обработчик капсул
            await capsule_text_handler(callback.message)
    except Exception as e:
        logging.error(f"Open capsule callback error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "referrals")
async def callback_referrals(callback: CallbackQuery):
    """Рефералы пользователя"""
    try:
        await callback.answer()
        if callback.message and callback.from_user:
            # Перенаправляем на текстовый обработчик рефералов
            await referrals_text_handler(callback.message)
    except Exception as e:
        logging.error(f"Referrals callback error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "leaderboard")
async def callback_leaderboard(callback: CallbackQuery):
    """Топ пользователей"""
    try:
        await callback.answer()
        if callback.message and callback.from_user:
            # Перенаправляем на текстовый обработчик топа
            # Простой лидерборд без отдельного хендлера
            text = "🏆 <b>Топ пользователей</b>\n\n📊 Функция в разработке\nСкоро здесь появится список лидеров!"
            await callback.message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Leaderboard callback error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "link_wallet")
async def callback_link_wallet(callback: CallbackQuery):
    """Привязать кошелек"""
    try:
        await callback.answer()
        if callback.message:
            text = "🔗 <b>Привязка кошелька</b>\n\nДля привязки кошелька воспользуйтесь кнопкой 'Stars Store' в главном меню."
            await callback.message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Link wallet callback error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "request_withdrawal")
async def callback_request_withdrawal(callback: CallbackQuery):
    """Запросить вывод"""
    try:
        await callback.answer()
        if callback.message:
            text = "💸 <b>Вывод средств</b>\n\nВывод средств будет доступен после привязки кошелька."
            await callback.message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Request withdrawal callback error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "share_link")
async def callback_share_link(callback: CallbackQuery):
    """Поделиться реферальной ссылкой"""
    try:
        await callback.answer()
        if callback.message and callback.from_user:
            user_id = callback.from_user.id
            referral_link = f"https://t.me/scReferalbot?start=ref_{user_id}"
            text = f"📱 <b>Ваша реферальная ссылка:</b>\n\n`{referral_link}`\n\nПоделитесь этой ссылкой с друзьями!"
            await callback.message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Share link callback error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "my_referrals")
async def callback_my_referrals(callback: CallbackQuery):
    """Мои рефералы"""
    try:
        await callback.answer()
        if callback.message and callback.from_user:
            # Перенаправляем на текстовый обработчик рефералов
            await referrals_text_handler(callback.message)
    except Exception as e:
        logging.error(f"My referrals callback error: {e}")
        await callback.answer("❌ Ошибка")

@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery):
    """Проверка подписки"""
    try:
        await callback.answer()
        if callback.message:
            text = "✅ <b>Проверка подписки</b>\n\nПроверка подписки в процессе..."
            await callback.message.answer(text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Check subscription callback error: {e}")
        await callback.answer("❌ Ошибка")