"""
Система ежедневного чек-ина для получения SC токенов
"""

from datetime import datetime, date
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from app.context import get_db, get_config

router = Router()

@router.callback_query(F.data == "daily_checkin")
async def daily_checkin_callback(callback: types.CallbackQuery):
    """Обработка ежедневного чек-ина"""
    if not callback.from_user:
        await callback.answer("❌ Ошибка системы", show_alert=True)
        return
    
    user_id = callback.from_user.id
    db = get_db()
    
    # Получаем текущую дату
    today = date.today().isoformat()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, делал ли пользователь чек-ин сегодня
            cursor.execute("""
                SELECT id FROM user_checkins 
                WHERE user_id = ? AND checkin_date = ?
            """, (user_id, today))
            
            existing_checkin = cursor.fetchone()
            
            if existing_checkin:
                await callback.answer("❌ Вы уже делали чек-ин сегодня!", show_alert=True)
                return
            
            # Проверяем, зарегистрирован ли пользователь и подписан
            cursor.execute("""
                SELECT subscription_checked, total_earnings 
                FROM users WHERE user_id = ?
            """, (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                await callback.answer("❌ Сначала зарегистрируйтесь в боте", show_alert=True)
                return
            
            if not user_data[0]:
                await callback.answer("❌ Сначала подтвердите подписку на канал", show_alert=True)
                return
            
            # Регистрируем чек-ин
            checkin_reward = 0.5
            cursor.execute("""
                INSERT INTO user_checkins (user_id, checkin_date, sc_amount)
                VALUES (?, ?, ?)
            """, (user_id, today, checkin_reward))
            
            # Начисляем награду пользователю
            cursor.execute("""
                UPDATE users 
                SET total_earnings = total_earnings + ?,
                    pending_balance = pending_balance + ?
                WHERE user_id = ?
            """, (checkin_reward, checkin_reward, user_id))
            
            conn.commit()
            
            # Получаем статистику чек-инов пользователя
            cursor.execute("""
                SELECT COUNT(*) FROM user_checkins WHERE user_id = ?
            """, (user_id,))
            total_checkins = cursor.fetchone()[0]
            
            # Получаем новый баланс
            cursor.execute("""
                SELECT pending_balance FROM users WHERE user_id = ?
            """, (user_id,))
            new_balance = cursor.fetchone()[0]
            
            success_text = (
                f"✅ <b>Ежедневный чек-ин выполнен!</b>\n\n"
                f"🎁 Получено: {checkin_reward} SC\n"
                f"💰 Ваш баланс: {new_balance:.2f} SC\n"
                f"📅 Всего чек-инов: {total_checkins}\n\n"
                f"💡 Возвращайтесь завтра за новой наградой!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            if callback.message and hasattr(callback.message, 'edit_text'):
                await callback.message.edit_text(success_text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer("🎉 Чек-ин выполнен!")
            
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
                f"🎁 Заработано: {total_earned:.2f} SC\n"
                f"📆 Последний чек-ин: {last_checkin}\n"
                f"✅ Сегодня: {'Выполнен' if today_checkin else 'Доступен'}\n\n"
                f"💡 Ежедневный чек-ин дает 0.5 SC!"
            )
            
            keyboard_buttons = []
            
            if not today_checkin:
                keyboard_buttons.append([InlineKeyboardButton(text="🎯 Сделать чек-ин", callback_data="daily_checkin")])
            
            keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            if callback.message and hasattr(callback.message, 'edit_text'):
                await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
            
    except Exception as e:
        logging.error(f"Checkin stats error for user {user_id}: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)