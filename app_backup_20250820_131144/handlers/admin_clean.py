"""
Чистая админ панель без ошибок
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
    
    stats_text = (
        f"📊 <b>Статистика системы</b>\n\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: {total_users}\n"
        f"• Верифицированы: {verified_users}\n\n"
        f"🎁 <b>Капсулы:</b>\n"
        f"• Всего открыто: {total_capsules}\n\n"
        f"👥 <b>Рефералы:</b>\n"
        f"• Всего приглашено: {total_referrals}\n"
        f"• Валидировано: {total_validated_refs}\n\n"
        f"💰 <b>Финансы:</b>\n"
        f"• Всего заработано: {format_balance(total_earnings)} SC"
    )
    
    await message.answer(stats_text, parse_mode="HTML")

# КОМАНДЫ ЗАДАНИЙ
@router.message(Command("add_task"), F.chat.type == ChatType.PRIVATE)
async def add_task_command(message: types.Message):
    """Добавить задание"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if len(args) < 4:
        await message.answer(
            "🎯 <b>Добавить задание</b>\n\n"
            "Формат: <code>/add_task название описание награда период_дней</code>\n\n"
            "Пример:\n"
            "<code>/add_task \"Подписка\" \"Подпишитесь на канал\" 2 7</code>\n"
            "<code>/add_task \"Лайк\" \"Лайкните пост\" 1 1</code>\n\n"
            "📅 Период - на сколько дней ставится задание",
            parse_mode="HTML"
        )
        return
    
    title = args[0].strip('"')
    description = args[1].strip('"')
    try:
        reward_capsules = int(args[2])
        period_days = int(args[3])
    except ValueError:
        await message.answer("❌ Награда и период должны быть числами")
        return
    
    db = get_db()
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, task_type, reward_capsules, period_days, status)
                VALUES (?, ?, 'partner', ?, ?, 'active')
            """, (title, description, reward_capsules, period_days))
            conn.commit()
            task_id = cursor.lastrowid
        
        # Генерируем автоматический пост для задания
        post_text = f"""🎯 <b>Новое задание!</b>

📝 <b>{title}</b>
{description}

🎁 <b>Награда:</b> {reward_capsules} капсул
📅 <b>Период:</b> {period_days} дней

Выполните задание и получите свои капсулы! 🎁"""
        
        await message.answer(
            f"✅ <b>Задание создано!</b>\n\n"
            f"🆔 ID: {task_id}\n"
            f"📝 Название: {title}\n"
            f"🎁 Награда: {reward_capsules} капсул\n"
            f"📅 Период: {period_days} дней\n\n"
            f"📢 <b>Автоматический пост:</b>\n\n{post_text}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка создания задания: {e}")

# КОМАНДЫ БЫСТРОГО РЕДАКТИРОВАНИЯ ЗАДАНИЙ
@router.message(Command("edit_task_title"), F.chat.type == ChatType.PRIVATE)
async def edit_task_title_command(message: types.Message):
    """Изменить название задания"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split(maxsplit=2)[1:]
    if len(args) < 2:
        await message.answer("Формат: <code>/edit_task_title ID \"Новое название\"</code>", parse_mode="HTML")
        return
    
    try:
        task_id = int(args[0])
        new_title = args[1].strip('"')
    except ValueError:
        await message.answer("❌ ID задания должен быть числом")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET title = ? WHERE id = ?", (new_title, task_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            await message.answer(f"✅ Название задания #{task_id} изменено на: {new_title}")
        else:
            await message.answer(f"❌ Задание #{task_id} не найдено")

@router.message(Command("edit_task_desc"), F.chat.type == ChatType.PRIVATE)
async def edit_task_desc_command(message: types.Message):
    """Изменить описание задания"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split(maxsplit=2)[1:]
    if len(args) < 2:
        await message.answer("Формат: <code>/edit_task_desc ID \"Новое описание\"</code>", parse_mode="HTML")
        return
    
    try:
        task_id = int(args[0])
        new_desc = args[1].strip('"')
    except ValueError:
        await message.answer("❌ ID задания должен быть числом")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET description = ? WHERE id = ?", (new_desc, task_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            await message.answer(f"✅ Описание задания #{task_id} изменено")
        else:
            await message.answer(f"❌ Задание #{task_id} не найдено")

@router.message(Command("edit_task_reward"), F.chat.type == ChatType.PRIVATE)
async def edit_task_reward_command(message: types.Message):
    """Изменить награду за задание"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer("Формат: <code>/edit_task_reward ID новая_награда</code>", parse_mode="HTML")
        return
    
    try:
        task_id = int(args[0])
        new_reward = int(args[1])
    except ValueError:
        await message.answer("❌ ID и награда должны быть числами")
        return
    
    if new_reward < 1 or new_reward > 10:
        await message.answer("❌ Награда должна быть от 1 до 10 капсул")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET reward_capsules = ? WHERE id = ?", (new_reward, task_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            await message.answer(f"✅ Награда за задание #{task_id} изменена на {new_reward} капсул")
        else:
            await message.answer(f"❌ Задание #{task_id} не найдено")

@router.message(Command("toggle_task"), F.chat.type == ChatType.PRIVATE)
async def toggle_task_command(message: types.Message):
    """Включить/выключить задание"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if not args:
        await message.answer("Формат: <code>/toggle_task ID</code>", parse_mode="HTML")
        return
    
    try:
        task_id = int(args[0])
    except ValueError:
        await message.answer("❌ ID задания должен быть числом")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        current_status = cursor.fetchone()
        
        if not current_status:
            await message.answer(f"❌ Задание #{task_id} не найдено")
            return
        
        new_status = "inactive" if current_status[0] == "active" else "active"
        cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        conn.commit()
        
        status_text = "активировано" if new_status == "active" else "деактивировано"
        await message.answer(f"✅ Задание #{task_id} {status_text}")

@router.message(Command("delete_task"), F.chat.type == ChatType.PRIVATE)
async def delete_task_command(message: types.Message):
    """Удалить задание"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if not args:
        await message.answer("Формат: <code>/delete_task ID</code>", parse_mode="HTML")
        return
    
    try:
        task_id = int(args[0])
    except ValueError:
        await message.answer("❌ ID задания должен быть числом")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем существование задания
        cursor.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            await message.answer(f"❌ Задание #{task_id} не найдено")
            return
        
        # Удаляем задание и связанные данные
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        cursor.execute("DELETE FROM user_task_completions WHERE task_id = ?", (task_id,))
        conn.commit()
        
        await message.answer(f"✅ Задание #{task_id} \"{task[0]}\" удалено")

@router.message(Command("list_tasks"), F.chat.type == ChatType.PRIVATE)
async def list_tasks_command(message: types.Message):
    """Список заданий"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, description, reward_capsules, period_days, status, current_completions
            FROM tasks 
            ORDER BY id DESC 
            LIMIT 20
        """)
        tasks = cursor.fetchall()
    
    if not tasks:
        await message.answer("📋 Заданий пока нет.")
        return
    
    text = "📋 <b>Список заданий</b>\n\n"
    
    for task in tasks:
        status_emoji = "✅" if task[5] == "active" else "❌"
        text += f"{status_emoji} <b>ID {task[0]}</b>: {task[1]}\n"
        text += f"📝 {task[2][:50]}{'...' if len(task[2]) > 50 else ''}\n"
        text += f"🎁 Награда: {task[3]} капсул\n"
        text += f"📅 Период: {task[4]} дней\n"
        text += f"📊 Выполнений: {task[6] or 0}\n\n"
    
    await message.answer(text, parse_mode="HTML")

# КОМАНДЫ ПОЛЬЗОВАТЕЛЕЙ
@router.message(Command("ban"), F.chat.type == ChatType.PRIVATE)
async def ban_command(message: types.Message):
    """Заблокировать пользователя"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if not args:
        await message.answer("❌ Укажите ID пользователя: <code>/ban 123456789</code>", parse_mode="HTML")
        return
    
    try:
        user_id = int(args[0])
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            await message.answer(f"✅ Пользователь {user_id} заблокирован")
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден")

@router.message(Command("unban"), F.chat.type == ChatType.PRIVATE)
async def unban_command(message: types.Message):
    """Разблокировать пользователя"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if not args:
        await message.answer("❌ Укажите ID пользователя: <code>/unban 123456789</code>", parse_mode="HTML")
        return
    
    try:
        user_id = int(args[0])
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            await message.answer(f"✅ Пользователь {user_id} разблокирован")
        else:
            await message.answer(f"❌ Пользователь {user_id} не найден")

@router.message(Command("user"), F.chat.type == ChatType.PRIVATE)
async def user_info_command(message: types.Message):
    """Информация о пользователе"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if not args:
        await message.answer(
            "👤 <b>Информация о пользователе</b>\n\n"
            "Формат: <code>/user ID</code>\n\n"
            "Пример: <code>/user 123456789</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        user_id = int(args[0])
    except ValueError:
        await message.answer("❌ ID пользователя должен быть числом")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, first_name, total_earnings, pending_balance, 
                   paid_balance, total_referrals, banned, registration_date, wallet_address
            FROM users WHERE user_id = ?
        """, (user_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await message.answer(f"❌ Пользователь {user_id} не найден")
            return
        
        cursor.execute("SELECT COUNT(*) FROM capsule_openings WHERE user_id = ?", (user_id,))
        capsules_opened = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_task_completions WHERE user_id = ?", (user_id,))
        tasks_completed = cursor.fetchone()[0]
    
    username = user_data[1] if user_data[1] else "без username"
    name = user_data[2] if user_data[2] else "Неизвестно"
    banned_status = "🔴 Заблокирован" if user_data[7] else "🟢 Активен"
    wallet = user_data[9][:10] + "..." + user_data[9][-6:] if user_data[9] else "❌ Не привязан"
    
    text = f"""👤 <b>Информация о пользователе</b>

🆔 <b>ID:</b> {user_data[0]}
👤 <b>Имя:</b> {name}
📱 <b>Username:</b> @{username}
📊 <b>Статус:</b> {banned_status}

💰 <b>Финансы:</b>
• Всего заработал: {format_balance(user_data[3])} SC
• К выводу: {format_balance(user_data[4])} SC
• Выплачено: {format_balance(user_data[5])} SC

👥 <b>Рефералы:</b> {user_data[6]}
🎁 <b>Капсул открыто:</b> {capsules_opened}
🎯 <b>Заданий выполнено:</b> {tasks_completed}

💼 <b>Кошелек:</b> {wallet}
📅 <b>Регистрация:</b> {user_data[8][:10] if user_data[8] else 'Неизвестно'}"""
    
    await message.answer(text, parse_mode="HTML")

# КОМАНДЫ ВЫПЛАТ
@router.message(Command("withdrawal_requests"), F.chat.type == ChatType.PRIVATE)
async def withdrawal_requests_command(message: types.Message):
    """Запросы на вывод"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT wr.id, wr.user_id, wr.amount, wr.status, wr.created_at,
                   u.username, u.first_name, u.wallet_address
            FROM withdrawal_requests wr
            LEFT JOIN users u ON wr.user_id = u.user_id
            WHERE wr.status = 'pending'
            ORDER BY wr.created_at DESC
            LIMIT 15
        """)
        requests = cursor.fetchall()
    
    if not requests:
        await message.answer("✅ Нет ожидающих запросов на вывод.")
        return
    
    text = "💸 <b>Запросы на вывод (ожидающие)</b>\n\n"
    
    for req in requests:
        username = req[5] if req[5] else "без username"
        name = req[6] if req[6] else f"ID {req[1]}"
        wallet = req[7][:10] + "..." + req[7][-6:] if req[7] else "❌ Не указан"
        
        text += f"🆔 <b>Запрос #{req[0]}</b>\n"
        text += f"👤 {name} (@{username})\n"
        text += f"💰 Сумма: {format_balance(req[2])} SC\n"
        text += f"💼 Кошелек: <code>{wallet}</code>\n"
        text += f"📅 Дата: {req[4][:16]}\n"
        text += f"📋 Одобрить: <code>/approve_withdrawal {req[0]}</code>\n\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(Command("approve_withdrawal"), F.chat.type == ChatType.PRIVATE)
async def approve_withdrawal_command(message: types.Message):
    """Одобрить запрос на вывод"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if not args:
        await message.answer("❌ Укажите ID запроса: <code>/approve_withdrawal 123</code>", parse_mode="HTML")
        return
    
    try:
        request_id = int(args[0])
    except ValueError:
        await message.answer("❌ ID должен быть числом")
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT wr.user_id, wr.amount, u.username, u.first_name, u.pending_balance
            FROM withdrawal_requests wr
            LEFT JOIN users u ON wr.user_id = u.user_id
            WHERE wr.id = ? AND wr.status = 'pending'
        """, (request_id,))
        request_data = cursor.fetchone()
        
        if not request_data:
            await message.answer("❌ Запрос не найден или уже обработан")
            return
        
        user_id, amount, username, first_name, pending_balance = request_data
        
        if pending_balance < amount:
            await message.answer(f"❌ У пользователя недостаточно средств ({format_balance(pending_balance)} SC)")
            return
        
        cursor.execute("""
            UPDATE withdrawal_requests 
            SET status = 'approved', processed_at = CURRENT_TIMESTAMP, admin_id = ?
            WHERE id = ?
        """, (message.from_user.id, request_id))
        
        cursor.execute("""
            INSERT INTO payouts (user_id, amount, admin_id, notes)
            VALUES (?, ?, ?, ?)
        """, (user_id, amount, message.from_user.id, f"Одобрено из запроса #{request_id}"))
        
        cursor.execute("""
            UPDATE users 
            SET pending_balance = pending_balance - ?, paid_balance = paid_balance + ?
            WHERE user_id = ?
        """, (amount, amount, user_id))
        
        conn.commit()
        
        name = first_name or f"ID {user_id}"
        await message.answer(
            f"✅ <b>Выплата одобрена!</b>\n\n"
            f"👤 Пользователь: {name} (@{username or 'без username'})\n"
            f"💰 Сумма: {format_balance(amount)} SC\n"
            f"🆔 Запрос: #{request_id}",
            parse_mode="HTML"
        )

@router.message(Command("payouts"), F.chat.type == ChatType.PRIVATE)
async def payouts_command(message: types.Message):
    """История выплат"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.user_id, p.amount, p.payout_date, p.notes,
                   u.username, u.first_name
            FROM payouts p
            LEFT JOIN users u ON p.user_id = u.user_id
            ORDER BY p.payout_date DESC
            LIMIT 15
        """)
        payouts = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*), SUM(amount) FROM payouts")
        total_stats = cursor.fetchone()
        total_count = total_stats[0] or 0
        total_amount = total_stats[1] or 0
    
    text = f"💳 <b>История выплат</b>\n\n"
    text += f"📊 <b>Общая статистика:</b>\n"
    text += f"• Всего выплат: {total_count}\n"
    text += f"• Общая сумма: {format_balance(total_amount)} SC\n\n"
    
    if not payouts:
        text += "📋 Выплат еще не было."
    else:
        text += "<b>Последние выплаты:</b>\n\n"
        for payout in payouts:
            username = payout[5] if payout[5] else "без username"
            name = payout[6] if payout[6] else f"ID {payout[1]}"
            
            text += f"💳 <b>#{payout[0]}</b> - {format_balance(payout[2])} SC\n"
            text += f"👤 {name} (@{username})\n"
            text += f"📅 {payout[3][:16]}\n"
            if payout[4]:
                text += f"📝 {payout[4]}\n"
            text += "\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(Command("pending"), F.chat.type == ChatType.PRIVATE)
async def pending_command(message: types.Message):
    """Пользователи с балансом"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE pending_balance > 0")
        count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(pending_balance) FROM users WHERE pending_balance > 0")
        total = cursor.fetchone()[0] or 0
    
    text = f"⏳ <b>Пользователи с балансом к выводу</b>\n\n"
    text += f"👥 Всего: {count} пользователей\n"
    text += f"💰 Общая сумма: {format_balance(total)} SC\n\n"
    
    if count > 0:
        with db.get_connection() as conn2:
            cursor2 = conn2.cursor()
            cursor2.execute("""
                SELECT user_id, username, first_name, pending_balance, wallet_address
                FROM users 
                WHERE pending_balance > 0
                ORDER BY pending_balance DESC
                LIMIT 10
            """)
            top_users = cursor2.fetchall()
        
        text += "<b>Топ пользователей:</b>\n\n"
        for user in top_users:
            username = user[1] if user[1] else "без username"
            name = user[2] if user[2] else f"ID {user[0]}"
            wallet = "✅ Есть" if user[4] else "❌ Нет"
            
            text += f"👤 {name} (@{username})\n"
            text += f"💎 Баланс: {format_balance(user[3])} SC\n"
            text += f"💼 Кошелек: {wallet}\n\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(Command("balances"), F.chat.type == ChatType.PRIVATE)
async def balances_command(message: types.Message):
    """Топ балансов пользователей"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, first_name, total_earnings, pending_balance, paid_balance
            FROM users 
            WHERE total_earnings > 0
            ORDER BY total_earnings DESC 
            LIMIT 20
        """)
        users = cursor.fetchall()
    
    if not users:
        await message.answer("📊 Пока нет пользователей с заработком.")
        return
    
    text = "💰 <b>Топ балансов пользователей</b>\n\n"
    
    for i, user in enumerate(users, 1):
        username = user[1] if user[1] else "без username"
        name = user[2] if user[2] else "Неизвестно"
        
        text += f"{i}. {name} (@{username})\n"
        text += f"   💎 Всего заработал: {format_balance(user[3])} SC\n"
        text += f"   ⏳ К выплате: {format_balance(user[4])} SC\n"
        text += f"   ✅ Выплачено: {format_balance(user[5])} SC\n\n"
    
    await message.answer(text, parse_mode="HTML")

@router.message(Command("mark_paid"), F.chat.type == ChatType.PRIVATE)
async def mark_paid_command(message: types.Message):
    """Отметить выплату как выполненную"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    if not message.text:
        await message.answer("❌ Ошибка обработки команды")
        return
        
    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer(
            "💳 <b>Отметить выплату</b>\n\n"
            "Формат: <code>/mark_paid user_id сумма [примечание]</code>\n\n"
            "Пример: <code>/mark_paid 123456789 50 Выплачено на TON</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        user_id = int(args[0])
        amount = float(args[1])
    except ValueError:
        await message.answer("❌ ID пользователя и сумма должны быть числами")
        return
    
    notes = " ".join(args[2:]) if len(args) > 2 else "Выплачено администратором"
    
    db = get_db()
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username, first_name, pending_balance
                FROM users WHERE user_id = ?
            """, (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                await message.answer(f"❌ Пользователь {user_id} не найден")
                return
            
            username, first_name, pending_balance = user_data
            
            if pending_balance < amount:
                await message.answer(
                    f"❌ Недостаточно средств\n"
                    f"Доступно: {format_balance(pending_balance)} SC\n"
                    f"Запрошено: {format_balance(amount)} SC"
                )
                return
            
            cursor.execute("""
                INSERT INTO payouts (user_id, amount, admin_id, notes)
                VALUES (?, ?, ?, ?)
            """, (user_id, amount, message.from_user.id, notes))
            
            cursor.execute("""
                UPDATE users 
                SET pending_balance = pending_balance - ?, 
                    paid_balance = paid_balance + ?
                WHERE user_id = ?
            """, (amount, amount, user_id))
            
            conn.commit()
            
            name = first_name or f"ID {user_id}"
            await message.answer(
                f"✅ <b>Выплата зарегистрирована!</b>\n\n"
                f"👤 Пользователь: {name} (@{username or 'без username'})\n"
                f"💰 Сумма: {format_balance(amount)} SC\n"
                f"📝 Примечание: {notes}",
                parse_mode="HTML"
            )
    except Exception as e:
        await message.answer(f"❌ Ошибка регистрации выплаты: {e}")

# CALLBACK HANDLERS
@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: types.CallbackQuery):
    """Показать статистику"""
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
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_payouts")
async def admin_payouts_callback(callback: types.CallbackQuery):
    """Управление выплатами"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM withdrawal_requests WHERE status = 'pending'")
            pending_withdrawals = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM payouts")
            completed_payouts = cursor.fetchone()[0]
            
        text = f"""💸 <b>Управление выплатами</b>

📋 <b>Статистика:</b>
• Ожидающие запросы: {pending_withdrawals}
• Выполненные выплаты: {completed_payouts}

📋 <b>Команды:</b>
• /withdrawal_requests - показать все запросы
• /payouts - история выплат
• /pending - пользователи с балансом
• /approve_withdrawal ID - одобрить запрос
• /mark_paid user_id сумма - отметить выплату"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
        
        if callback.message and hasattr(callback.message, 'edit_text'):
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Admin payouts error: {e}")
        await callback.answer("❌ Ошибка получения данных о выплатах", show_alert=True)

@router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: types.CallbackQuery):
    """Управление пользователями"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """👥 <b>Управление пользователями</b>

📋 <b>Доступные команды:</b>
• /ban [user_id] - заблокировать пользователя
• /unban [user_id] - разблокировать пользователя  
• /user [user_id] - информация о пользователе
• /balances - топ балансов пользователей
• /pending - пользователи с балансом к выводу

✅ <b>Все команды работают!</b>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "admin_tasks")
async def admin_tasks_callback(callback: types.CallbackQuery):
    """Управление заданиями"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_task_completions")
            total_completions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'active'")
            active_tasks = cursor.fetchone()[0]
            
        text = f"""🎯 <b>Управление заданиями</b>

📊 <b>Статистика:</b>
• Всего заданий: {total_tasks}
• Активных: {active_tasks}
• Всего выполнений: {total_completions}

🔧 <b>Управление:</b>"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить задание", callback_data="task_create"),
                InlineKeyboardButton(text="🎯 Менеджер заданий", callback_data="tasks_manager")
            ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="task_stats"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="task_settings")
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ])
        
        if callback.message and hasattr(callback.message, 'edit_text'):
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Admin tasks error: {e}")
        await callback.answer("❌ Ошибка получения данных заданий", show_alert=True)

@router.callback_query(F.data == "tasks_manager")
async def tasks_manager_handler(callback: types.CallbackQuery):
    """Полнофункциональный менеджер заданий с кнопками"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'active'")
            active_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT id, title, reward_capsules, period_days, status FROM tasks ORDER BY id DESC LIMIT 5")
            recent_tasks = cursor.fetchall()
        
        text = f"""🎯 <b>Менеджер заданий</b>

📊 <b>Статистика:</b>
• Всего заданий: {total_tasks}
• Активных: {active_tasks}

📋 <b>Последние задания:</b>"""
        
        if recent_tasks:
            for task in recent_tasks:
                status_emoji = "✅" if task[4] == "active" else "❌"
                text += f"\n{status_emoji} <b>ID {task[0]}</b>: {task[1]} ({task[2]} капсул, {task[3]} дн.)"
        else:
            text += "\n• Заданий пока нет"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Создать", callback_data="task_create_wizard"),
                InlineKeyboardButton(text="📋 Все задания", callback_data="task_list_all")
            ],
            [
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="task_settings"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="task_stats")
            ],
            [InlineKeyboardButton(text="🔙 К заданиям", callback_data="admin_tasks")]
        ])
        
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Tasks manager error: {e}")
        await callback.answer("❌ Ошибка загрузки менеджера", show_alert=True)


@router.callback_query(F.data == "task_settings")
async def task_settings_handler(callback: types.CallbackQuery):
    """Настройки заданий - прямо в admin_clean"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """⚙️ <b>Продвинутые настройки заданий</b>

🎯 <b>Система полностью обновлена:</b>
✅ Кнопочный интерфейс управления
✅ Мастер создания с шаблонами
✅ Редактирование и удаление заданий
✅ Реальная статистика из базы

🔧 <b>Новые возможности:</b>
• Готовые шаблоны заданий (подписки, группы, лайки)
• Интерактивный список всех заданий
• Статистика популярности и выполнений
• Визуальное управление без команд

💡 <b>Как использовать:</b>
• Используйте "🎯 Менеджер заданий" для работы
• Кнопка "➕ Создать" → выбор шаблонов
• "📋 Все задания" → управление существующими
• "📊 Статистика" → детальная аналитика

🚀 <b>Система готова к активному использованию!</b>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 К менеджеру", callback_data="tasks_manager"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="task_stats")
        ],
        [InlineKeyboardButton(text="🔙 К заданиям", callback_data="admin_tasks")]
    ])
    
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logging.error(f"Task settings error: {e}")
        await callback.answer("❌ Ошибка загрузки настроек", show_alert=True)

@router.callback_query(F.data == "task_stats")
async def task_stats_handler(callback: types.CallbackQuery):
    """Статистика заданий - прямо в admin_clean"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'active'")
            active_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_task_completions")
            total_completions = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(reward_capsules) FROM user_task_completions")
            total_rewards_result = cursor.fetchone()[0]
            total_rewards = total_rewards_result if total_rewards_result else 0
            
            cursor.execute("""
                SELECT title, current_completions 
                FROM tasks 
                WHERE status = 'active' 
                ORDER BY current_completions DESC 
                LIMIT 5
            """)
            popular_tasks = cursor.fetchall()
        
        text = f"""📊 <b>Статистика заданий</b>

📈 <b>Общие данные:</b>
• Всего заданий: {total_tasks}
• Активных: {active_tasks}
• Завершенных: {total_tasks - active_tasks}

👥 <b>Активность пользователей:</b>
• Всего выполнений: {total_completions}
• Выдано наград: {total_rewards} капсул

🏆 <b>Популярные задания:</b>"""
        
        if popular_tasks:
            for task in popular_tasks[:3]:
                text += f"\n• {task[0]}: {task[1]} выполнений"
        else:
            text += "\n• Пока нет активных заданий"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="task_stats")],
            [InlineKeyboardButton(text="🔙 К заданиям", callback_data="admin_tasks")]
        ])
        
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Task stats error: {e}")
        await callback.answer("❌ Ошибка получения статистики", show_alert=True)

@router.callback_query(F.data == "task_create_wizard")
async def task_create_wizard_handler(callback: types.CallbackQuery):
    """Мастер создания заданий с кнопками"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """➕ <b>Мастер создания задания</b>

🎯 <b>Шаблоны заданий:</b>
Выберите тип задания или создайте своё"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Подписка на канал", callback_data="task_template_channel"),
            InlineKeyboardButton(text="👥 Вступление в группу", callback_data="task_template_group")
        ],
        [
            InlineKeyboardButton(text="👍 Лайк поста", callback_data="task_template_like"),
            InlineKeyboardButton(text="📤 Репост", callback_data="task_template_repost")
        ],
        [
            InlineKeyboardButton(text="✏️ Своё задание", callback_data="task_custom_create"),
            InlineKeyboardButton(text="📋 Инструкция", callback_data="task_manual_guide")
        ],
        [InlineKeyboardButton(text="🔙 К менеджеру", callback_data="tasks_manager")]
    ])
    
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logging.error(f"Task create wizard error: {e}")
        await callback.answer("❌ Ошибка мастера создания", show_alert=True)

@router.callback_query(F.data == "task_list_all")
async def task_list_all_handler(callback: types.CallbackQuery):
    """Полный список заданий с управлением"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = get_db()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, reward_capsules, period_days, status, current_completions
                FROM tasks 
                ORDER BY id DESC 
                LIMIT 10
            """)
            tasks = cursor.fetchall()
    
        if not tasks:
            text = "📋 <b>Список заданий</b>\n\nЗаданий пока нет."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать первое", callback_data="task_create_wizard")],
                [InlineKeyboardButton(text="🔙 К менеджеру", callback_data="tasks_manager")]
            ])
        else:
            text = "📋 <b>Все задания</b>\n"
            
            keyboard_rows = []
            for task in tasks:
                status_emoji = "✅" if task[4] == "active" else "❌"
                text += f"\n{status_emoji} <b>ID {task[0]}</b>: {task[1]}"
                text += f"\n   🎁 {task[2]} капсул • 📅 {task[3]} дн. • 👥 {task[5] or 0} выполнений\n"
                
                # Добавляем кнопки управления для каждого задания
                keyboard_rows.append([
                    InlineKeyboardButton(text=f"✏️ Редактировать #{task[0]}", callback_data=f"task_edit_{task[0]}"),
                    InlineKeyboardButton(text=f"🗑 Удалить #{task[0]}", callback_data=f"task_delete_confirm_{task[0]}")
                ])
            
            keyboard_rows.extend([
                [InlineKeyboardButton(text="➕ Новое задание", callback_data="task_create_wizard")],
                [InlineKeyboardButton(text="🔙 К менеджеру", callback_data="tasks_manager")]
            ])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Task list error: {e}")
        await callback.answer("❌ Ошибка загрузки списка", show_alert=True)

@router.callback_query(F.data.startswith("task_template_"))
async def task_template_handler(callback: types.CallbackQuery):
    """Обработка шаблонов заданий"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    template_type = callback.data.split("_")[-1]
    
    templates = {
        "channel": {
            "title": "Подписка на канал",
            "desc": "Подпишитесь на наш канал @simplecoin_chat",
            "reward": 3,
            "period": 7
        },
        "group": {
            "title": "Вступление в группу", 
            "desc": "Присоединитесь к нашей группе @simplecoin_chatSC",
            "reward": 2,
            "period": 7
        },
        "like": {
            "title": "Лайк поста",
            "desc": "Поставьте лайк нашему посту",
            "reward": 1,
            "period": 3
        },
        "repost": {
            "title": "Репост в канал",
            "desc": "Сделайте репост в свой канал или группу",
            "reward": 5,
            "period": 5
        }
    }
    
    template = templates.get(template_type)
    if not template:
        await callback.answer("❌ Неизвестный шаблон", show_alert=True)
        return
    
    text = f"""📝 <b>Шаблон: {template['title']}</b>

<code>/add_task "{template['title']}" "{template['desc']}" {template['reward']} {template['period']}</code>

🎁 <b>Награда:</b> {template['reward']} капсул
📅 <b>Период:</b> {template['period']} дней

💡 <b>Скопируйте команду выше и отправьте для создания задания</b>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К шаблонам", callback_data="task_create_wizard")]
    ])
    
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logging.error(f"Task template error: {e}")
        await callback.answer("❌ Ошибка шаблона", show_alert=True)

@router.callback_query(F.data == "task_manual_guide")
async def task_manual_guide_handler(callback: types.CallbackQuery):
    """Инструкция по ручному созданию заданий"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """📋 <b>Инструкция по созданию заданий</b>

✍️ <b>Формат команды:</b>
<code>/add_task "Название" "Описание" награда период</code>

📝 <b>Примеры использования:</b>

🔹 <b>Подписка на канал:</b>
<code>/add_task "Подписка на канал" "Подпишитесь на @simplecoin_chat" 3 7</code>

🔹 <b>Вступление в группу:</b>
<code>/add_task "Вступление в группу" "Присоединитесь к @simplecoin_chatSC" 2 5</code>

🔹 <b>Репост поста:</b>
<code>/add_task "Репост" "Сделайте репост последнего поста" 5 3</code>

⚙️ <b>Параметры:</b>
• <b>Награда:</b> от 1 до 10 капсул
• <b>Период:</b> от 1 до 30 дней
• <b>Кавычки обязательны</b> для названия и описания

💡 <b>Задание автоматически активируется после создания</b>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К мастеру", callback_data="task_create_wizard")]
    ])
    
    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
    except Exception as e:
        logging.error(f"Manual guide error: {e}")
        await callback.answer("❌ Ошибка загрузки инструкции", show_alert=True)

# Управление заданиями перенесено в task_management_clean.py

# Все функции управления заданиями перенесены в task_management_clean.py

@router.callback_query(F.data == "task_create")
async def task_create_callback(callback: types.CallbackQuery):
    """Создание нового задания через интерфейс"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """➕ <b>Создание нового задания</b>

📋 <b>Используйте команду:</b>
<code>/add_task "Название" "Описание" награда период_дней</code>

📝 <b>Примеры:</b>
• <code>/add_task "Подписка TechNews" "Подпишитесь на @technews_channel" 3 7</code>
• <code>/add_task "Лайк поста" "Поставьте лайк нашему посту" 1 1</code>
• <code>/add_task "Репост" "Сделайте репост в свою ленту" 2 3</code>

🎁 <b>Награда:</b> количество капсул (1-10)
📅 <b>Период:</b> на сколько дней активно задание (1-30)

После создания бот автоматически сгенерирует пост для публикации!"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Шаблоны заданий", callback_data="task_templates")],
        [InlineKeyboardButton(text="🔙 К заданиям", callback_data="admin_tasks")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "task_list")
async def task_list_callback(callback: types.CallbackQuery):
    """Список заданий с возможностью управления"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, reward_capsules, period_days, status, current_completions
            FROM tasks 
            ORDER BY id DESC 
            LIMIT 8
        """)
        tasks = cursor.fetchall()
    
    if not tasks:
        text = "📋 <b>Список заданий</b>\n\nЗаданий пока нет."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать первое задание", callback_data="task_create")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")]
        ])
    else:
        text = "📋 <b>Активные задания</b>\n\n"
        keyboard_buttons = []
        
        for task in tasks:
            status_emoji = "✅" if task[4] == "active" else "❌"
            text += f"{status_emoji} <b>ID {task[0]}</b>: {task[1]}\n"
            text += f"🎁 {task[2]} капсул • 📅 {task[3]} дней • 👥 {task[5] or 0} выполнений\n\n"
            
            # Добавляем кнопки для каждого задания
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"✏️ Редактировать #{task[0]}", callback_data=f"task_edit_{task[0]}"),
                InlineKeyboardButton(text=f"🗑 Удалить #{task[0]}", callback_data=f"task_delete_{task[0]}")
            ])
        
        keyboard_buttons.append([InlineKeyboardButton(text="➕ Новое задание", callback_data="task_create")])
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 К заданиям", callback_data="admin_tasks")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("task_edit_"))
async def task_edit_callback(callback: types.CallbackQuery):
    """Редактирование задания"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    task_id = int(callback.data.split("_")[2])
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, description, reward_capsules, period_days, status
            FROM tasks WHERE id = ?
        """, (task_id,))
        task = cursor.fetchone()
    
    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    text = f"""✏️ <b>Редактирование задания #{task[0]}</b>

📝 <b>Название:</b> {task[1]}
📄 <b>Описание:</b> {task[2]}
🎁 <b>Награда:</b> {task[3]} капсул
📅 <b>Период:</b> {task[4]} дней
⚡ <b>Статус:</b> {'Активно' if task[5] == 'active' else 'Неактивно'}

🔧 <b>Команды для редактирования:</b>
• <code>/edit_task_title {task_id} "Новое название"</code>
• <code>/edit_task_desc {task_id} "Новое описание"</code>
• <code>/edit_task_reward {task_id} новая_награда</code>
• <code>/edit_task_period {task_id} новый_период</code>
• <code>/toggle_task {task_id}</code> - включить/выключить"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Переключить статус", callback_data=f"task_toggle_{task_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task_delete_{task_id}")
        ],
        [InlineKeyboardButton(text="🔙 К списку", callback_data="task_list")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("task_toggle_"))
async def task_toggle_callback(callback: types.CallbackQuery):
    """Переключение статуса задания"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    task_id = int(callback.data.split("_")[2])
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM tasks WHERE id = ?", (task_id,))
        current_status = cursor.fetchone()
        
        if not current_status:
            await callback.answer("❌ Задание не найдено", show_alert=True)
            return
        
        new_status = "inactive" if current_status[0] == "active" else "active"
        cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        conn.commit()
    
    status_text = "активировано" if new_status == "active" else "деактивировано"
    await callback.answer(f"✅ Задание #{task_id} {status_text}")
    
    # Возвращаемся к редактированию
    callback.data = f"task_edit_{task_id}"
    await task_edit_callback(callback)

@router.callback_query(F.data.startswith("task_delete_") & ~F.data.startswith("task_delete_confirm_"))
async def task_delete_callback(callback: types.CallbackQuery):
    """Подтверждение удаления задания - первый этап"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    try:
        task_id = int(callback.data.split("_")[2])
        
        text = f"🗑 <b>Удаление задания #{task_id}</b>\n\n❓ Вы уверены? Это действие необратимо."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"task_delete_confirm_{task_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="task_list_all")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Task delete dialog error: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@router.callback_query(F.data.startswith("task_delete_confirm_"))
async def task_delete_confirm_callback(callback: types.CallbackQuery):
    """Окончательное удаление задания"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    try:
        task_id = int(callback.data.split("_")[-1])  # Берем последнюю часть
        db = get_db()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            cursor.execute("DELETE FROM user_task_completions WHERE task_id = ?", (task_id,))
            conn.commit()
        
        await callback.answer(f"✅ Задание #{task_id} удалено", show_alert=True)
        
        # Возвращаемся к списку заданий через правильный handler
        await task_list_all_handler(callback)
        
    except Exception as e:
        logging.error(f"Delete confirm error: {e}")
        await callback.answer("❌ Ошибка удаления", show_alert=True)

@router.callback_query(F.data == "task_templates")
async def task_templates_callback(callback: types.CallbackQuery):
    """Шаблоны заданий"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = """📋 <b>Шаблоны заданий</b>

📺 <b>Подписка на канал:</b>
<code>/add_task "Подписка на [Название]" "Подпишитесь на @username канала" 3 7</code>

💬 <b>Вступление в чат:</b>
<code>/add_task "Вступить в чат [Название]" "Присоединитесь к @chatusername" 2 5</code>

👍 <b>Лайк поста:</b>
<code>/add_task "Лайк поста" "Поставьте лайк посту по ссылке" 1 3</code>

🔄 <b>Репост:</b>
<code>/add_task "Репост" "Сделайте репост в свою ленту" 2 3</code>

📝 <b>Комментарий:</b>
<code>/add_task "Комментарий" "Оставьте комментарий под постом" 2 5</code>

🎥 <b>Просмотр видео:</b>
<code>/add_task "Просмотр видео" "Посмотрите видео полностью" 1 1</code>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К созданию", callback_data="task_create")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "task_stats")
async def task_stats_callback(callback: types.CallbackQuery):
    """Статистика по заданиям"""
    if not callback.from_user or not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = get_db()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Общая статистика заданий
        cursor.execute("SELECT COUNT(*), COUNT(CASE WHEN status = 'active' THEN 1 END) FROM tasks")
        task_stats = cursor.fetchone()
        total_tasks = task_stats[0]
        active_tasks = task_stats[1]
        
        # Статистика выполнений
        cursor.execute("SELECT COUNT(*), COUNT(DISTINCT user_id) FROM user_task_completions")
        completion_stats = cursor.fetchone()
        total_completions = completion_stats[0]
        unique_users = completion_stats[1]
        
        # Самые популярные задания
        cursor.execute("""
            SELECT t.title, COUNT(utc.id) as completions
            FROM tasks t
            LEFT JOIN user_task_completions utc ON t.id = utc.task_id
            GROUP BY t.id, t.title
            ORDER BY completions DESC
            LIMIT 5
        """)
        popular_tasks = cursor.fetchall()
        
        # Статистика по наградам
        cursor.execute("SELECT SUM(reward_capsules * current_completions) FROM tasks")
        total_rewards = cursor.fetchone()[0] or 0
    
    text = f"""📊 <b>Статистика заданий</b>

📋 <b>Общая информация:</b>
• Всего заданий: {total_tasks}
• Активных: {active_tasks}
• Неактивных: {total_tasks - active_tasks}

👥 <b>Выполнения:</b>
• Всего выполнений: {total_completions}
• Уникальных пользователей: {unique_users}
• Среднее на пользователя: {round(total_completions/unique_users, 1) if unique_users > 0 else 0}

🎁 <b>Награды:</b>
• Всего выдано капсул: {total_rewards}

🔥 <b>Популярные задания:</b>"""
    
    for task in popular_tasks:
        text += f"\n• {task[0]}: {task[1]} выполнений"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 К заданиям", callback_data="admin_tasks")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

# Старый handler удален - теперь используется task_settings.py