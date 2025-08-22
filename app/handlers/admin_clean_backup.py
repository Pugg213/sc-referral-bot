"""
Полная восстановленная админ панель с исправленными LSP ошибками
Восстановлены ВСЕ функции из оригинала
"""

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatType
import logging
from typing import Optional

from app.context import get_db, get_config

router = Router()

def is_admin(user_id: int) -> bool:
    """Проверка админа"""
    cfg = get_config()
    return user_id in cfg.ADMIN_IDS

def format_balance(amount: float) -> str:
    """Форматирование баланса"""
    return f"{amount:.2f}"

# ===== ОСНОВНЫЕ КОМАНДЫ АДМИН ПАНЕЛИ =====

@router.message(Command("admin"), F.chat.type == ChatType.PRIVATE)
async def admin_panel(message: types.Message):
    """Главная админ панель"""
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ панели.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="💸 Выплаты", callback_data="admin_payouts")
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
            InlineKeyboardButton(text="🎯 Задания", callback_data="admin_tasks")
        ]
    ])
    
    await message.answer(
        "🛠 <b>Панель администратора</b>\n\n"
        "Выберите раздел для управления:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.message(Command("stats"), F.chat.type == ChatType.PRIVATE)
async def show_stats(message: types.Message):
    """Показать статистику системы"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_checked = 1")
        verified_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM capsule_openings")
        total_capsules = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(validated_referrals) FROM users")
        total_validated_refs_result = cursor.fetchone()[0] 
        total_validated_refs = total_validated_refs_result if total_validated_refs_result else 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL")
        total_referrals = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total_earnings) FROM users")
        total_earnings_result = cursor.fetchone()[0]
        total_earnings = total_earnings_result if total_earnings_result else 0
        
        cursor.execute("SELECT SUM(pending_balance) FROM users")
        pending_balance_result = cursor.fetchone()[0]
        pending_balance = pending_balance_result if pending_balance_result else 0
        
        cursor.execute("SELECT SUM(paid_balance) FROM users")
        paid_balance_result = cursor.fetchone()[0] 
        paid_balance = paid_balance_result if paid_balance_result else 0

    text = f"""📊 <b>Полная статистика системы</b>

👥 <b>Пользователи:</b>
• Всего зарегистрировано: {total_users}
• Прошли верификацию: {verified_users}

🎁 <b>Капсулы:</b>
• Всего открыто: {total_capsules}

👥 <b>Рефералы:</b>
• Всего приглашено: {total_referrals}
• Валидированных: {total_validated_refs}

💰 <b>Финансы:</b>
• Всего заработано: {format_balance(total_earnings)} SC
• К выплате: {format_balance(pending_balance)} SC  
• Выплачено: {format_balance(paid_balance)} SC"""
    
    await message.answer(text, parse_mode="HTML")

# ===== УПРАВЛЕНИЕ ЗАДАНИЯМИ =====

@router.message(Command("add_task"), F.chat.type == ChatType.PRIVATE)
async def add_task_command(message: types.Message):
    """Добавить новое задание"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    # Парсим аргументы: /add_task "Название" "Описание" награда_капсул дни
    args = message.text.split(maxsplit=1) if message.text else []
    if len(args) < 2:
        await message.answer(
            "❌ <b>Неверный формат!</b>\n\n"
            "Использование:\n"
            "<code>/add_task \"Название задания\" \"Описание задания\" количество_капсул дни</code>\n\n"
            "Пример:\n"
            "<code>/add_task \"Подписка на канал\" \"Подпишитесь на @simplecoin_chat\" 3 7</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        # Простой парсинг аргументов
        parts = args[1].split()
        if len(parts) < 4:
            raise ValueError("Недостаточно аргументов")
            
        # Извлекаем название и описание из кавычек
        text_parts = args[1]
        
        # Ищем кавычки для названия
        first_quote = text_parts.find('"')
        if first_quote == -1:
            raise ValueError("Название должно быть в кавычках")
            
        second_quote = text_parts.find('"', first_quote + 1)
        if second_quote == -1:
            raise ValueError("Название должно быть в кавычках")
            
        title = text_parts[first_quote + 1:second_quote]
        
        # Ищем кавычки для описания
        remaining = text_parts[second_quote + 1:].strip()
        third_quote = remaining.find('"')
        if third_quote == -1:
            raise ValueError("Описание должно быть в кавычках")
            
        fourth_quote = remaining.find('"', third_quote + 1)
        if fourth_quote == -1:
            raise ValueError("Описание должно быть в кавычках")
            
        description = remaining[third_quote + 1:fourth_quote]
        
        # Извлекаем числовые параметры
        remaining_params = remaining[fourth_quote + 1:].strip().split()
        if len(remaining_params) < 2:
            raise ValueError("Недостаточно параметров")
            
        reward_capsules = int(remaining_params[0])
        period_days = int(remaining_params[1])
        
        if reward_capsules <= 0 or period_days <= 0:
            raise ValueError("Награда и период должны быть положительными числами")
        
    except (ValueError, IndexError) as e:
        await message.answer(
            f"❌ <b>Ошибка в параметрах:</b> {str(e)}\n\n"
            "Правильный формат:\n"
            "<code>/add_task \"Название\" \"Описание\" капсулы дни</code>",
            parse_mode="HTML"
        )
        return
    
    # Добавляем задание в БД
    db = get_db()
    
    try:
        task_id = db.add_task(
            title=title,
            description=description, 
            task_type="manual",
            reward_capsules=reward_capsules,
            partner_name="",
            partner_url="",
            requirements="",
            expires_at=None,
            max_completions=None
        )
        
        await message.answer(
            f"✅ <b>Задание создано!</b>\n\n"
            f"🆔 ID: {task_id}\n"
            f"📝 Название: {title}\n"
            f"📄 Описание: {description}\n"
            f"🎁 Награда: {reward_capsules} капсул\n"
            f"📅 Период: {period_days} дней\n\n"
            f"Используйте /list_tasks для просмотра всех заданий.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error adding task: {e}")
        await message.answer("❌ Ошибка при добавлении задания.")

@router.message(Command("list_tasks"), F.chat.type == ChatType.PRIVATE)
async def list_tasks_command(message: types.Message):
    """Показать список всех заданий"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    db = get_db()
    tasks = db.get_all_tasks()
    
    if not tasks:
        await message.answer("📋 <b>Заданий пока нет</b>\n\nИспользуйте /add_task для создания.", parse_mode="HTML")
        return
    
    text = "📋 <b>Все задания:</b>\n\n"
    
    for task in tasks:
        status_emoji = "✅" if task.get('status') == 'active' else "❌"
        text += f"{status_emoji} <b>ID {task.get('id')}</b>: {task.get('title')}\n"
        text += f"🎁 {task.get('reward_capsules', 0)} капсул • "
        text += f"📅 {task.get('period_days', 0)} дн. • "
        text += f"👥 {task.get('current_completions', 0)} выполнений\n\n"
    
    text += "💡 <b>Команды управления:</b>\n"
    text += "• <code>/toggle_task ID</code> - включить/выключить\n" 
    text += "• <code>/delete_task ID</code> - удалить задание\n"
    text += "• <code>/edit_task_* ID параметр</code> - редактировать"
    
    await message.answer(text, parse_mode="HTML")

# ===== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ =====

@router.message(Command("user_info"), F.chat.type == ChatType.PRIVATE)
async def user_info_command(message: types.Message):
    """Получить информацию о пользователе"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    args = message.text.split() if message.text else []
    if len(args) < 2:
        await message.answer(
            "❌ Укажите ID пользователя:\n<code>/user_info 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
        return
    
    db = get_db()
    user = db.get_user(user_id)
    
    if not user:
        await message.answer(f"❌ Пользователь {user_id} не найден.")
        return
    
    # Дополнительная информация
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Количество рефералов
        cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id = ?", (user_id,))
        total_refs = cursor.fetchone()[0]
        
        # Последние капсулы  
        cursor.execute("""
            SELECT reward_name, reward_amount, opened_at 
            FROM capsule_openings 
            WHERE user_id = ? 
            ORDER BY opened_at DESC LIMIT 3
        """, (user_id,))
        recent_capsules = cursor.fetchall()
    
    text = f"""👤 <b>Информация о пользователе</b>

🆔 <b>ID:</b> {user.get('user_id')}
👤 <b>Username:</b> @{user.get('username', 'неизвестно')}
🏷 <b>Имя:</b> {user.get('first_name', 'неизвестно')}
📅 <b>Регистрация:</b> {user.get('registration_date', 'неизвестно')[:10]}

✅ <b>Статус:</b>
• Подписка проверена: {'Да' if user.get('subscription_checked') else 'Нет'}
• Забанен: {'Да' if user.get('banned') else 'Нет'}

💰 <b>Финансы:</b>  
• Всего заработано: {format_balance(user.get('total_earnings', 0))} SC
• К выплате: {format_balance(user.get('pending_balance', 0))} SC
• Выплачено: {format_balance(user.get('paid_balance', 0))} SC

👥 <b>Рефералы:</b>
• Приглашено: {total_refs}
• Валидировано: {user.get('validated_referrals', 0)}

🎁 <b>Капсулы:</b>
• Сегодня открыто: {user.get('daily_capsules_opened', 0)}/3
• Всего открыто: {user.get('total_capsules_opened', 0)}"""

    if recent_capsules:
        text += "\n\n🎁 <b>Последние капсулы:</b>\n"
        for capsule in recent_capsules:
            text += f"• {capsule[0]}: {capsule[1]} ({capsule[2][:10]})\n"

    await message.answer(text, parse_mode="HTML")

# ===== УПРАВЛЕНИЕ ВЫПЛАТАМИ =====

@router.message(Command("withdrawal_requests"), F.chat.type == ChatType.PRIVATE) 
async def withdrawal_requests_command(message: types.Message):
    """Показать запросы на вывод средств"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    db = get_db()
    requests = db.get_withdrawal_requests()
    
    if not requests:
        await message.answer("📋 <b>Запросов на вывод нет</b>", parse_mode="HTML")
        return
    
    text = "💸 <b>Запросы на вывод средств:</b>\n\n"
    
    for req in requests:
        text += f"🆔 <b>#{req.get('id')}</b>\n"
        text += f"👤 @{req.get('username', 'неизвестно')} ({req.get('user_id')})\n"
        text += f"💰 Сумма: {format_balance(req.get('amount', 0))} SC\n"
        text += f"📅 Дата: {req.get('created_at', '')[:16]}\n"
        text += f"👛 Кошелек: {req.get('wallet_address', 'не указан')}\n\n"
    
    text += "💡 Для одобрения используйте:\n<code>/approve_withdrawal ID</code>"
    
    await message.answer(text, parse_mode="HTML")

# ===== CALLBACK HANDLERS =====

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: types.CallbackQuery):
    """Показать статистику системы через callback"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_checked = 1")
            verified_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(total_earnings) FROM users")
            total_earnings_result = cursor.fetchone()[0]
            total_earnings = total_earnings_result if total_earnings_result else 0
            
        text = f"""📊 <b>Общая статистика</b>

👥 <b>Пользователи:</b>
• Всего: {total_users}
• Верифицированы: {verified_users}

💰 <b>Финансы:</b>
• Всего заработано: {format_balance(total_earnings)} SC"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
        
        if callback.message and hasattr(callback.message, 'edit_text'):
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Admin stats error: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)

@router.callback_query(F.data == "admin_back")
async def admin_back_callback(callback: types.CallbackQuery):
    """Возврат к главному меню"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="💸 Выплаты", callback_data="admin_payouts")
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
            InlineKeyboardButton(text="🎯 Задания", callback_data="admin_tasks")
        ]
    ])
    
    text = "🛠 <b>Панель администратора</b>\n\nВыберите раздел для управления:"
    
    if callback.message and hasattr(callback.message, 'edit_text') and callback.message.edit_text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_tasks")
async def admin_tasks_callback(callback: types.CallbackQuery):
    """Управление заданиями"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """🎯 <b>Менеджер заданий</b>

📝 <b>Управление заданиями:</b>
• Создавать новые задания
• Редактировать существующие
• Активировать/деактивировать
• Просматривать статистику выполнений

💡 <b>Команды:</b>
<code>/add_task "Название" "Описание" награда_капсул дни</code>
<code>/list_tasks</code> - список всех заданий
<code>/toggle_task ID</code> - включить/выключить задание"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text') and callback.message.edit_text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_payouts")
async def admin_payouts_callback(callback: types.CallbackQuery):
    """Управление выплатами"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """💸 <b>Управление выплатами</b>

📊 <b>Доступные команды:</b>
• <code>/withdrawal_requests</code> - запросы на вывод
• <code>/approve_withdrawal ID</code> - одобрить выплату
• <code>/payouts</code> - история выплат
• <code>/balances</code> - управление балансами"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text') and callback.message.edit_text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: types.CallbackQuery):
    """Управление пользователями"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """👥 <b>Управление пользователями</b>

📊 <b>Доступные команды:</b>
• <code>/user_info ID</code> - информация о пользователе
• <code>/ban ID причина</code> - заблокировать пользователя
• <code>/unban ID</code> - разблокировать пользователя"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text') and callback.message.edit_text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()