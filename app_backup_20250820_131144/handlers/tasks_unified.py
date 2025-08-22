"""
Единая система управления заданиями - объединяет все функции без дублирования
"""
import logging
from datetime import datetime
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.context import get_config, get_db
from app.keyboards import get_tasks_keyboard
from app.helpers.task_verification import verify_subscription, is_valid_telegram_url

router = Router()

class TaskCreation(StatesGroup):
    """Состояния создания задания"""
    waiting_url = State()
    waiting_reward = State()

# ================== ПОЛЬЗОВАТЕЛИ ==================
@router.message(F.text == "🎯 Задания")
async def tasks_menu(message: types.Message):
    """Главное меню заданий для пользователей"""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    db = get_db()
    
    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        return
    
    # Статистика пользователя
    completed_tasks = db.get_user_completed_tasks(user_id)
    active_tasks = db.get_active_tasks()
    
    available_tasks = []
    for task in active_tasks:
        if not db.is_task_completed(user_id, task['id']):
            if task['max_completions'] is None or task['current_completions'] < task['max_completions']:
                available_tasks.append(task)
    
    total_earned_capsules = sum(ct['reward_capsules'] for ct in completed_tasks)
    
    text = (
        f"🎯 <b>Система заданий</b>\n\n"
        f"💼 Выполняйте задания от партнеров и получайте бонусные капсулы!\n\n"
        f"📊 <b>Ваша статистика:</b>\n"
        f"✅ Выполнено: {len(completed_tasks)} заданий\n"
        f"🎁 Заработано: {total_earned_capsules} капсул\n"
        f"📋 Доступно: {len(available_tasks)} заданий"
    )
    
    await message.answer(text, reply_markup=get_tasks_keyboard())

@router.callback_query(F.data == "available_tasks")
async def show_available_tasks(callback: CallbackQuery):
    """Показать доступные задания"""
    if not callback.from_user:
        return
    
    user_id = callback.from_user.id
    db = get_db()
    
    active_tasks = db.get_active_tasks()
    if not active_tasks:
        await callback.message.edit_text("📋 Пока нет доступных заданий")
        return
    
    # Фильтруем только невыполненные
    available_tasks = []
    for task in active_tasks:
        if not db.is_task_completed(user_id, task['id']):
            if task['max_completions'] is None or task['current_completions'] < task['max_completions']:
                available_tasks.append(task)
    
    if not available_tasks:
        text = "✅ Вы выполнили все доступные задания!\n\nСледите за новыми заданиями от партнеров."
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data="tasks_back")]]
        )
        await callback.message.edit_text(text, reply_markup=keyboard)
        return
    
    text = f"📋 <b>Доступные задания ({len(available_tasks)}):</b>\n\n"
    keyboard_buttons = []
    
    for task in available_tasks:
        type_emoji = "📢" if task['task_type'] == 'channel_subscription' else "👥"
        text += (
            f"{type_emoji} <b>{task['title']}</b>\n"
            f"🏢 Партнер: {task['partner_name']}\n"
            f"🎁 Награда: {task['reward_capsules']} капсул\n"
            f"👤 Выполнили: {task['current_completions']}\n\n"
        )
        
        keyboard_buttons.append([
            types.InlineKeyboardButton(
                text=f"{type_emoji} {task['title'][:25]}...",
                callback_data=f"do_task_{task['id']}"
            )
        ])
    
    keyboard_buttons.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="tasks_back")])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("do_task_"))
async def execute_task(callback: CallbackQuery):
    """Выполнить задание пользователем"""
    if not callback.from_user:
        return
    
    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[2])
    
    db = get_db()
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    if task['status'] != 'active':
        await callback.answer("❌ Задание больше не доступно", show_alert=True)
        return
    
    if db.is_task_completed(user_id, task_id):
        await callback.answer("✅ Вы уже выполнили это задание", show_alert=True)
        return
    
    type_emoji = "📢" if task['task_type'] == 'channel_subscription' else "👥"
    action_text = "подпишитесь на канал" if task['task_type'] == 'channel_subscription' else "вступите в группу"
    
    text = (
        f"{type_emoji} <b>{task['title']}</b>\n\n"
        f"🏢 <b>Партнер:</b> {task['partner_name']}\n"
        f"📝 <b>Описание:</b> {task['description']}\n"
        f"🎁 <b>Награда:</b> {task['reward_capsules']} бонусных капсул\n\n"
        f"📋 <b>Что нужно сделать:</b>\n"
        f"1. Нажмите кнопку '{action_text}' ниже\n"
        f"2. {action_text.capitalize()} по ссылке\n"
        f"3. Нажмите 'Проверить выполнение'\n"
        f"4. Получите бонусные капсулы!\n\n"
        f"⚠️ <b>Важно:</b> Не отписывайтесь сразу, иначе награда будет аннулирована."
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text=f"{type_emoji} {action_text.capitalize()}", 
            url=task['partner_url']
        )],
        [types.InlineKeyboardButton(
            text="✅ Проверить выполнение", 
            callback_data=f"check_task_{task_id}"
        )],
        [types.InlineKeyboardButton(text="🔙 К заданиям", callback_data="available_tasks")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("check_task_"))
async def check_task_completion(callback: CallbackQuery):
    """Проверить выполнение задания"""
    if not callback.from_user or not callback.message or not callback.message.bot:
        return
    
    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[2])
    
    db = get_db()
    task = db.get_task(task_id)
    
    if not task or task['status'] != 'active':
        await callback.answer("❌ Задание недоступно", show_alert=True)
        return
    
    if db.is_task_completed(user_id, task_id):
        await callback.answer("✅ Задание уже выполнено", show_alert=True)
        return
    
    # Проверить выполнение задания
    # Используем partner_url вместо target_url (правильное поле в БД)
    subscription_verified, error_message = await verify_subscription(
        callback.message.bot, 
        user_id, 
        task['partner_url'], 
        task['task_type']
    )
    
    if subscription_verified:
        # Засчитать выполнение задания
        db.complete_user_task(user_id, task_id, task['reward_capsules'])
        db.add_bonus_capsules(user_id, task['reward_capsules'])
        
        success_text = (
            f"🎉 <b>Задание выполнено!</b>\n\n"
            f"✅ {task['title']}\n"
            f"🎁 Получено: {task['reward_capsules']} бонусных капсул\n"
            f"📦 Капсулы добавлены к вашему ежедневному лимиту\n\n"
            f"💡 Спасибо за поддержку наших партнеров!"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🎯 Другие задания", callback_data="available_tasks")],
            [types.InlineKeyboardButton(text="📦 Открыть капсулы", callback_data="open_capsule")],
            [types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(success_text, reply_markup=keyboard)
        
        # Уведомить администраторов (если включено)
        cfg = get_config()
        if not getattr(cfg, 'DISABLE_ADMIN_NOTIFICATIONS', False):
            user_info = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.first_name
            admin_notification = f"✅ Задание выполнено\n👤 {user_info}\n🎯 {task['title']}\n🎁 {task['reward_capsules']} капсул"
            
            for admin_id in cfg.ADMIN_IDS:
                try:
                    await callback.message.bot.send_message(admin_id, admin_notification)
                except:
                    pass
                
    else:
        # Задание не выполнено
        error_text = (
            f"❌ <b>Задание не выполнено</b>\n\n"
            f"🎯 {task['title']}\n"
            f"🔍 Проблема: {error_message or 'Подписка не найдена'}\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"1. Убедитесь что вы подписались\n"
            f"2. Подождите 1-2 минуты\n" 
            f"3. Попробуйте проверить еще раз\n\n"
            f"💡 Если проблема повторяется, обратитесь к админу"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Проверить еще раз", callback_data=f"check_task_{task_id}")],
            [types.InlineKeyboardButton(text="🔙 К заданиям", callback_data="available_tasks")]
        ])
        
        await callback.message.edit_text(error_text, reply_markup=keyboard)

# ================== АДМИНЫ - КОМАНДЫ ==================
@router.message(Command("tasks"))
async def admin_tasks_command(message: types.Message):
    """Быстрый просмотр заданий для админов"""
    if not message.from_user:
        return
    
    cfg = get_config()
    if message.from_user.id not in cfg.ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return
    
    db = get_db()
    tasks = db.get_active_tasks()
    
    if not tasks:
        await message.answer("📋 Активных заданий нет")
        return
    
    text = f"📋 <b>Активные задания ({len(tasks)}):</b>\n\n"
    
    for task in tasks:
        text += (
            f"🆔 <b>ID {task['id']}</b> - {task['title']}\n"
            f"   🏢 {task['partner_name']}\n"
            f"   👤 Выполнили: {task['current_completions']}\n"
            f"   🎁 Награда: {task['reward_capsules']} капсул\n\n"
        )
    
    text += "⚡ <b>Управление:</b>\n/off ID - отключить\n/new - создать"
    
    await message.answer(text)

@router.message(Command("off"))
async def disable_task_command(message: types.Message):
    """Быстро отключить задание"""
    if not message.from_user or not message.text:
        return
    
    cfg = get_config()
    if message.from_user.id not in cfg.ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return
    
    parts = message.text.strip().split()
    if len(parts) < 2:
        await message.answer("📝 Использование: /off ID\nПример: /off 1")
        return
    
    try:
        task_id = int(parts[1])
    except ValueError:
        await message.answer("❌ ID должно быть числом")
        return
    
    db = get_db()
    task = db.get_task(task_id)
    
    if not task:
        await message.answer(f"❌ Задание ID {task_id} не найдено")
        return
    
    if task['status'] != 'active':
        await message.answer("❌ Задание уже отключено")
        return
    
    if db.deactivate_task(task_id):
        await message.answer(f"✅ Задание отключено\n🆔 ID {task_id}: {task['title']}")
    else:
        await message.answer("❌ Ошибка при отключении")

@router.message(Command("new"))
async def create_task_command(message: types.Message):
    """Создание задания через команду"""
    if not message.from_user:
        return
    
    cfg = get_config()
    if message.from_user.id not in cfg.ADMIN_IDS:
        await message.answer("❌ Доступ запрещен")
        return
    
    await message.answer(
        "🎯 <b>Создание задания</b>\n\n"
        "📝 Используйте кнопки в разделе 'Задания' для создания через простой интерфейс\n\n"
        "💡 Или команду:\n/tasks - посмотреть все"
    )

# ================== АДМИНЫ - МЕНЮ ==================
@router.callback_query(F.data == "admin_tasks")
async def admin_tasks_menu(callback: CallbackQuery):
    """Админское меню управления заданиями"""
    if not callback.from_user:
        return
    
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db = get_db()
    active_tasks = db.get_active_tasks()
    total_tasks = len(active_tasks) if active_tasks else 0
    total_completions = sum(task['current_completions'] for task in active_tasks) if active_tasks else 0
    
    text = (
        f"🎯 <b>Управление заданиями</b>\n\n"
        f"📊 <b>Статистика:</b>\n"
        f"📋 Активных заданий: {total_tasks}\n"
        f"✅ Всего выполнений: {total_completions}\n\n"
        f"💡 Создавайте задания для увеличения активности пользователей"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Создать задание", callback_data="create_task_start")],
        [
            types.InlineKeyboardButton(text="📋 Список заданий", callback_data="admin_list_tasks"),
            types.InlineKeyboardButton(text="🗑️ Удалить задание", callback_data="admin_delete_tasks")
        ],
        [types.InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "create_task_start")
async def start_task_creation(callback: CallbackQuery, state: FSMContext):
    """Начать создание задания"""
    if not callback.from_user:
        return
    
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    text = (
        "🎯 <b>Создание нового задания</b>\n\n"
        "📝 <b>Простой процесс:</b>\n"
        "1. Выберите тип задания\n"
        "2. Укажите ссылку\n"
        "3. Выберите награду\n"
        "4. Готово!\n\n"
        "💡 Название и описание создаются автоматически"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📢 Подписка на канал", callback_data="type_channel")],
        [types.InlineKeyboardButton(text="👥 Вступление в группу", callback_data="type_group")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("type_"))
async def select_task_type(callback: CallbackQuery, state: FSMContext):
    """Выбрать тип задания"""
    task_type = callback.data.split("_")[1]
    
    if task_type == "channel":
        await state.update_data(task_type="channel_subscription", type_name="канал")
        text = "📢 <b>Подписка на канал</b>\n\nВведите ссылку на канал:"
    else:
        await state.update_data(task_type="group_join", type_name="группу")
        text = "👥 <b>Вступление в группу</b>\n\nВведите ссылку на группу:"
    
    await state.set_state(TaskCreation.waiting_url)
    await callback.message.edit_text(text)

@router.message(TaskCreation.waiting_url)
async def process_task_url(message: types.Message, state: FSMContext):
    """Обработать URL задания"""
    if not message.text or not message.text.startswith(('https://t.me/', 'http://t.me/', 't.me/')):
        await message.answer("❌ Введите корректную ссылку на Telegram канал или группу")
        return
    
    data = await state.get_data()
    url = message.text
    type_name = data.get('type_name', 'ресурс')
    
    # Создать название автоматически
    if 'channel' in data.get('task_type', ''):
        title = f"🔔 Подпишись на {url.split('/')[-1] if '/' in url else 'канал'}"
        partner_name = url.split('/')[-1] if '/' in url else "Партнер"
    else:
        title = f"💬 Вступи в {url.split('/')[-1] if '/' in url else 'группу'}"
        partner_name = url.split('/')[-1] if '/' in url else "Партнер"
    
    await state.update_data(partner_url=url, title=title, partner_name=partner_name)
    
    text = (
        f"🎁 <b>Выберите награду за {type_name}:</b>\n\n"
        f"📢 Ссылка: {url}\n"
        f"🎯 Название: {title}\n\n"
        f"💡 Стандартные награды:"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎁 3 капсулы", callback_data="reward_3")],
        [types.InlineKeyboardButton(text="🎁 5 капсул", callback_data="reward_5")],
        [types.InlineKeyboardButton(text="🎁 7 капсул", callback_data="reward_7")],
        [types.InlineKeyboardButton(text="✏️ Другая награда", callback_data="reward_custom")]
    ])
    
    await state.set_state(TaskCreation.waiting_reward)
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("reward_"))
async def select_reward(callback: CallbackQuery, state: FSMContext):
    """Выбрать награду"""
    reward_data = callback.data.split("_")[1]
    
    if reward_data == "custom":
        await callback.message.edit_text("✏️ <b>Введите количество капсул (от 1 до 15):</b>")
        return
    
    try:
        reward = int(reward_data)
    except ValueError:
        await callback.answer("❌ Неверная награда", show_alert=True)
        return
    
    await finalize_task_creation(callback, state, reward)

@router.message(TaskCreation.waiting_reward)
async def process_custom_reward(message: types.Message, state: FSMContext):
    """Обработать пользовательскую награду"""
    try:
        reward = int(message.text)
        if reward < 1 or reward > 15:
            await message.answer("❌ Награда должна быть от 1 до 15 капсул")
            return
    except ValueError:
        await message.answer("❌ Введите число от 1 до 15")
        return
    
    # Создаем фиктивный callback для использования в finalize_task_creation
    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.answer = lambda text="", show_alert=False: None
    
    fake_callback = FakeCallback(message)
    await finalize_task_creation(fake_callback, state, reward)

async def finalize_task_creation(callback, state: FSMContext, reward: int):
    """Завершить создание задания"""
    data = await state.get_data()
    
    task_data = {
        'task_type': data['task_type'],
        'title': data['title'],
        'description': f"Выполните задание и получите {reward} бонусных капсул",
        'partner_name': data['partner_name'],
        'partner_url': data['partner_url'],
        'reward_capsules': reward,
        'max_completions': None,
        'status': 'active'
    }
    
    db = get_db()
    task_id = db.create_task(task_data)
    
    if task_id:
        success_text = (
            f"✅ <b>Задание создано!</b>\n\n"
            f"🆔 ID: {task_id}\n"
            f"🎯 {data['title']}\n"
            f"🏢 Партнер: {data['partner_name']}\n"
            f"🎁 Награда: {reward} капсул\n"
            f"🔗 Ссылка: {data['partner_url']}\n\n"
            f"🎉 Задание сразу доступно пользователям!"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Создать еще", callback_data="create_task_start")],
            [types.InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_tasks")]
        ])
        
        if hasattr(callback.message, 'edit_text'):
            await callback.message.edit_text(success_text, reply_markup=keyboard)
        else:
            await callback.message.answer(success_text, reply_markup=keyboard)
    else:
        error_text = "❌ Ошибка при создании задания"
        if hasattr(callback.message, 'edit_text'):
            await callback.message.edit_text(error_text)
        else:
            await callback.message.answer(error_text)
    
    await state.clear()

# ================== ОБЩИЕ ФУНКЦИИ ==================
@router.callback_query(F.data == "tasks_back")
async def tasks_back(callback: CallbackQuery):
    """Вернуться в главное меню заданий"""
    await tasks_menu(callback.message)

@router.callback_query(F.data == "admin_delete_tasks")
async def admin_delete_tasks(callback: CallbackQuery):
    """Удаление заданий"""
    if not callback.from_user:
        return
    
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db = get_db()
    tasks = db.get_all_tasks()
    
    if not tasks:
        text = "📋 <b>Нет заданий для удаления</b>"
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        return
    
    text = "🗑️ <b>Выберите задание для удаления:</b>\n\n"
    keyboard_buttons = []
    
    for task in tasks[:10]:  # Показать первые 10
        status_emoji = "✅" if task['status'] == 'active' else "❌"
        type_emoji = "📢" if task['task_type'] == 'channel_subscription' else "👥"
        
        text += (
            f"{status_emoji} <b>ID {task['id']}</b> {type_emoji} {task['title']}\n"
            f"   👤 Выполнили: {task['current_completions']}\n\n"
        )
        
        keyboard_buttons.append([
            types.InlineKeyboardButton(
                text=f"🗑️ Удалить ID {task['id']}", 
                callback_data=f"delete_task_{task['id']}"
            )
        ])
    
    keyboard_buttons.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("delete_task_"))
async def confirm_delete_task(callback: CallbackQuery):
    """Подтверждение удаления задания"""
    if not callback.from_user:
        return
    
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    task_id = int(callback.data.split("_")[2])
    db = get_db()
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    text = (
        f"⚠️ <b>Подтвердите удаление</b>\n\n"
        f"🆔 ID: {task_id}\n"
        f"🎯 Название: {task['title']}\n"
        f"🏢 Партнер: {task['partner_name']}\n"
        f"👤 Выполнили: {task['current_completions']} человек\n\n"
        f"❗ <b>Внимание:</b> Это действие нельзя отменить!\n"
        f"История выполнений пользователей сохранится."
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Удалить", callback_data=f"confirm_delete_{task_id}"),
            types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_delete_tasks")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("confirm_delete_"))
async def execute_delete_task(callback: CallbackQuery):
    """Выполнить удаление задания"""
    if not callback.from_user:
        return
    
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    task_id = int(callback.data.split("_")[2])
    db = get_db()
    
    # Удаляем задание из базы данных
    success = db.delete_task(task_id)
    
    if success:
        text = (
            f"✅ <b>Задание удалено!</b>\n\n"
            f"🆔 ID {task_id} успешно удален из системы\n"
            f"📋 История выполнений пользователей сохранена\n\n"
            f"💡 Задание больше не доступно пользователям"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🗑️ Удалить еще", callback_data="admin_delete_tasks")],
            [types.InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_tasks")]
        ])
    else:
        text = "❌ <b>Ошибка при удалении задания</b>\n\nПопробуйте еще раз или обратитесь к разработчику."
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_delete_tasks")]
        ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_list_tasks")
async def admin_list_tasks(callback: CallbackQuery):
    """Список всех заданий для админа"""
    if not callback.from_user:
        return
    
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    db = get_db()
    tasks = db.get_all_tasks()  # Получить все задания
    
    if not tasks:
        text = "📋 <b>Заданий пока нет</b>\n\nСоздайте первое задание для пользователей!"
    else:
        text = f"📋 <b>Все задания ({len(tasks)}):</b>\n\n"
        
        active_count = 0
        for task in tasks:
            status_emoji = "✅" if task['status'] == 'active' else "❌"
            type_emoji = "📢" if task['task_type'] == 'channel_subscription' else "👥"
            
            if task['status'] == 'active':
                active_count += 1
            
            text += (
                f"{status_emoji} <b>ID {task['id']}</b> {type_emoji} {task['title']}\n"
                f"   🏢 {task['partner_name']}\n"
                f"   👤 Выполнили: {task['current_completions']}\n"
                f"   🎁 {task['reward_capsules']} капсул\n\n"
            )
        
        text += f"📊 Активных: {active_count}, Всего: {len(tasks)}"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)