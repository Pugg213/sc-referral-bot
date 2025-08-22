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
        
        await message.answer(rules_text, reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Rules text error: {e}")
        await message.answer("❌ Ошибка загрузки правил")

@router.message(F.text == "🎯 Задания", F.chat.type == ChatType.PRIVATE)
async def tasks_text_handler(message: Message):
    """Обработчик текста 'Задания' """
    try:
        tasks_text = """📋 <b>Доступные задания</b>

🎯 <b>Активные задания:</b>
В данный момент нет активных заданий от партнеров.

🔔 <b>Уведомления:</b>
Новые задания появляются регулярно. Следите за обновлениями!

💡 <b>Типы заданий:</b>
• Подписки на каналы партнеров
• Участие в розыгрышах
• Репосты и комментарии
• Приглашение друзей в проекты

🎁 <b>Награды за задания:</b>
• Бонусные капсулы
• Увеличенный множитель удачи
• Дополнительные SC токены"""
        
        await message.answer(tasks_text, reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Tasks text error: {e}")
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
            
            # Безопасное редактирование сообщения
            if callback.message:
                try:
                    await callback.message.edit_text(success_text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
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
            
            # Безопасное редактирование сообщения
            if callback.message:
                try:
                    await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
                    await callback.message.answer(stats_text, reply_markup=keyboard, parse_mode="HTML")
            
            await callback.answer()
            
    except Exception as e:
        logging.error(f"Checkin stats error for user {user_id}: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)