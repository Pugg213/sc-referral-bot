"""
Единая система управления заданиями - объединяет все функции без дублирования
"""
import logging
import json
from datetime import datetime
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.context import get_config, get_db
from app.keyboards import get_tasks_keyboard
from app.helpers.task_verification import verify_subscription, is_valid_telegram_url
from app.services.tasks import TaskService

router = Router()

# Helper function for safe message editing
async def safe_edit_message(callback, text, reply_markup=None, parse_mode="HTML"):
    """Безопасное редактирование сообщения с fallback"""
    # КРИТИЧЕСКАЯ ПРОВЕРКА: callback должен быть CallbackQuery, а не строкой
    if not callback or isinstance(callback, str) or not hasattr(callback, 'message'):
        return
    
    if hasattr(callback.message, 'edit_text'):
        try:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception:
            try:
                await callback.answer(text[:200] + "..." if len(text) > 200 else text, show_alert=True)
            except:
                logging.error("Failed to answer callback in safe_edit_message")
    else:
        try:
            await callback.answer(text[:200] + "..." if len(text) > 200 else text, show_alert=True)
        except:
            logging.error("Failed to answer callback in safe_edit_message fallback")

class TaskCreation(StatesGroup):
    """Состояния создания задания"""
    waiting_url = State()
    waiting_activity_params = State()  # Новое состояние для параметров активности
    waiting_reward = State()

class TaskEditing(StatesGroup):
    """Состояния редактирования задания"""
    waiting_title = State()
    waiting_description = State()
    waiting_reward = State()
    waiting_activity_params = State()

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
        f"📋 Доступно: {len(available_tasks)} заданий\n\n"
    )
    
    # Показываем активные задания прямо в меню
    if available_tasks:
        text += f"🔥 <b>Активные задания:</b>\n"
        for task in available_tasks[:3]:  # Показываем первые 3 задания
            # Определяем эмодзи по типу задания
            if task['task_type'] == 'channel_subscription':
                type_emoji = "📢"
            elif task['task_type'] == 'channel_activity':
                type_emoji = "💬"
            else:
                type_emoji = "👥"
                
            text += f"{type_emoji} {task['title']}\n"
            text += f"   🎁 {task['reward_capsules']} капсул • 🏢 {task['partner_name']}\n"
        
        if len(available_tasks) > 3:
            text += f"\n... и ещё {len(available_tasks) - 3} заданий"
    else:
        text += f"📭 <b>Нет активных заданий</b>\n\nНовые задания появятся в ближайшее время!"
    
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
        await safe_edit_message(callback, "📋 Пока нет доступных заданий")
        return
    
    # Фильтруем только невыполненные
    available_tasks = []
    for task in active_tasks:
        is_completed = db.is_task_completed(user_id, task['id'])
        has_max_completions = task['max_completions'] is not None
        at_max_completions = has_max_completions and task['current_completions'] >= task['max_completions']
        
        
        if not is_completed and not at_max_completions:
            available_tasks.append(task)
    
    if not available_tasks:
        text = "✅ Вы выполнили все доступные задания!\n\nСледите за новыми заданиями от партнеров."
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data="tasks_back")]]
        )
        if callback.message and hasattr(callback.message, 'edit_text'):
            try:
                await safe_edit_message(callback, text, reply_markup=keyboard)
            except Exception:
                await callback.answer("✅ Все задания выполнены!", show_alert=True)
        return
    
    text = f"📋 <b>Доступные задания ({len(available_tasks)}):</b>\n\n"
    keyboard_buttons = []
    
    for task in available_tasks:
        # Определяем эмодзи по типу задания
        if task['task_type'] == 'channel_subscription':
            type_emoji = "📢"
        elif task['task_type'] == 'channel_activity':
            type_emoji = "💬"
        else:
            type_emoji = "👥"
            
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
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        try:
            await safe_edit_message(callback, text, reply_markup=keyboard)
        except Exception:
            await callback.answer("📋 Задания загружены!", show_alert=True)

@router.callback_query(F.data.startswith("do_task_"))
async def execute_task(callback: CallbackQuery):
    """Выполнить задание пользователем"""
    if not callback.from_user:
        return
    
    user_id = callback.from_user.id
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
    
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
    
    # Определяем эмодзи и текст действия по типу задания
    if task['task_type'] == 'channel_subscription':
        type_emoji = "📢"
        action_text = "подпишитесь на канал"
        is_activity_task = False
    elif task['task_type'] == 'channel_activity':
        type_emoji = "💬"
        action_text = "выполните активность в канале"
        is_activity_task = True
    else:
        type_emoji = "👥"
        action_text = "вступите в группу"
        is_activity_task = False
    
    # Разные инструкции для разных типов заданий
    if task['task_type'] == 'channel_activity':
        # Для заданий на активность - особые инструкции
        text = (
            f"{type_emoji} <b>{task['title']}</b>\n\n"
            f"🏢 <b>Партнер:</b> {task['partner_name']}\n"
            f"{task['description']}\n\n"
            f"🎁 <b>Награда:</b> {task['reward_capsules']} бонусных капсул\n\n"
            f"📋 <b>Пошаговая инструкция:</b>\n"
            f"1️⃣ Нажмите кнопку 'Перейти в канал'\n"
            f"2️⃣ Подпишитесь на канал (если не подписаны)\n"
            f"3️⃣ Оставьте комментарии под постами в канале\n"
            f"4️⃣ Вернитесь сюда и нажмите 'Проверить выполнение'\n\n"
            f"✨ После проверки получите свои капсулы!"
        )
    else:
        # Обычные задания (подписка/вступление)
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
    
    # Разные кнопки для разных типов заданий
    if task['task_type'] == 'channel_activity':
        button_text = "🔗 Перейти в канал"
    else:
        button_text = f"{type_emoji} {action_text.capitalize()}"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text=button_text, 
            url=task['partner_url']
        )],
        [types.InlineKeyboardButton(
            text="✅ Проверить выполнение", 
            callback_data=f"check_task_{task_id}"
        )],
        [types.InlineKeyboardButton(text="🔙 К заданиям", callback_data="available_tasks")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        try:
            await safe_edit_message(callback, text, reply_markup=keyboard)
        except Exception:
            await callback.answer("🎯 Задание загружено!", show_alert=True)

@router.callback_query(F.data.startswith("check_task_"))
async def check_task_completion(callback: CallbackQuery):
    """Проверить выполнение задания"""
    if not callback.from_user or not callback.message or not callback.message.bot:
        return
    
    user_id = callback.from_user.id
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
    
    db = get_db()
    task = db.get_task(task_id)
    
    if not task or task['status'] != 'active':
        await callback.answer("❌ Задание недоступно", show_alert=True)
        return
    
    if db.is_task_completed(user_id, task_id):
        await callback.answer("✅ Задание уже выполнено", show_alert=True)
        return
    
    # Проверить выполнение задания с помощью правильной логики
    task_service = TaskService(db)
    
    # Создаем объект Task для проверки
    from app.services.tasks import Task, TaskType
    task_obj = Task(
        id=task['id'],
        title=task['title'],
        description=task['description'],
        task_type=TaskType(task['task_type']),
        requirements=eval(task['requirements']) if task['requirements'] else {},
        reward_sc=task.get('reward_sc', 0.0),
        reward_capsules=task['reward_capsules'],
        partner_name=task.get('partner_name', ''),
        partner_url=task.get('partner_url', ''),
        expires_at=None,
        max_completions=task.get('max_completions'),
        created_at=None
    )
    
    verification_result = await task_service._verify_task_completion(user_id, task_obj, callback.message.bot)
    
    if verification_result["success"]:
        # Засчитать выполнение задания (только капсулы)
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
        
        if callback.message and hasattr(callback.message, 'edit_text'):
            try:
                await safe_edit_message(callback, success_text, reply_markup=keyboard)
            except Exception:
                await callback.answer("🎉 Задание выполнено!", show_alert=True)
        
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
        error_message = verification_result.get("error", "Требования не выполнены")
        error_text = (
            f"❌ <b>Задание не выполнено</b>\n\n"
            f"🎯 {task['title']}\n"
            f"🔍 Проблема: {error_message}\n\n"
            f"📝 <b>Что делать:</b>\n"
            f"1. Убедитесь что вы выполнили требования\n"
            f"2. Подождите 1-2 минуты\n" 
            f"3. Попробуйте проверить еще раз\n\n"
            f"💡 Если проблема повторяется, обратитесь к админу"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔄 Проверить еще раз", callback_data=f"check_task_{task_id}")],
            [types.InlineKeyboardButton(text="🔙 К заданиям", callback_data="available_tasks")]
        ])
        
        if callback.message and hasattr(callback.message, 'edit_text'):
            try:
                await safe_edit_message(callback, error_text, reply_markup=keyboard)
            except Exception:
                await callback.answer("❌ Задание не выполнено", show_alert=True)

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
    
    if not message.text:
        await message.answer("❌ Введите команду с ID")
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
# УДАЛЕН: Конфликтующий обработчик admin_tasks - перенесен в admin_clean.py
# Теперь все админ функции в одном месте

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
        [types.InlineKeyboardButton(text="💬 Активность в канале", callback_data="type_activity")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")]
    ])
    
    if callback.message and hasattr(callback.message, 'edit_text'):
        try:
            await safe_edit_message(callback, text, reply_markup=keyboard)
        except Exception:
            await callback.answer("🎯 Создание задания", show_alert=True)

@router.callback_query(F.data.startswith("type_"))
async def select_task_type(callback: CallbackQuery, state: FSMContext):
    """Выбрать тип задания"""
    if not callback.data or len(callback.data.split("_")) < 2:
        return
    task_type = callback.data.split("_")[1]
    
    if task_type == "channel":
        await state.update_data(task_type="channel_subscription", type_name="канал")
        text = "📢 <b>Подписка на канал</b>\n\nВведите ссылку на канал:"
    elif task_type == "activity":
        await state.update_data(task_type="channel_activity", type_name="активность")
        text = "💬 <b>Активность в канале</b>\n\nВведите username канала (например: @simplecoin_news):"
    else:
        await state.update_data(task_type="group_join", type_name="группу")
        text = "👥 <b>Вступление в группу</b>\n\nВведите ссылку на группу:"
    
    await state.set_state(TaskCreation.waiting_url)
    if callback.message and hasattr(callback.message, 'edit_text'):
        try:
            await safe_edit_message(callback, text)
        except Exception:
            await callback.answer(text, show_alert=True)
    else:
        await callback.answer(text, show_alert=True)

@router.message(TaskCreation.waiting_url)
async def process_task_url(message: types.Message, state: FSMContext):
    """Обработать URL задания"""
    logging.info(f"🔧 Processing URL: {message.text}, user: {message.from_user.id if message.from_user else 'unknown'}")
    data = await state.get_data()
    task_type = data.get('task_type', '')
    logging.info(f"🔧 Current task_type: {task_type}, data: {data}")
    
    if task_type == "channel_activity":
        # Для активности в канале принимаем @username
        if not message.text or not (message.text.startswith('@') or message.text.startswith('https://t.me/')):
            await message.answer("❌ Введите username канала (@simplecoin_news) или ссылку на канал")
            return
        
        channel = message.text
        if channel.startswith('https://t.me/'):
            channel = '@' + channel.split('/')[-1]
        elif not channel.startswith('@'):
            channel = '@' + channel
        
        title = f"💬 Активность в {channel}"
        partner_name = channel.replace('@', '')
        url = f"https://t.me/{partner_name}"
        
        await state.update_data(
            partner_url=url, 
            title=title, 
            partner_name=partner_name,
            channel=channel
        )
    else:
        # Для подписки и групп требуем полную ссылку
        if not message.text or not message.text.startswith(('https://t.me/', 'http://t.me/', 't.me/')):
            await message.answer("❌ Введите корректную ссылку на Telegram канал или группу")
            return
        
        url = message.text
        type_name = data.get('type_name', 'ресурс')
        
        # Создать название автоматически
        if 'channel' in task_type:
            title = f"🔔 Подпишись на {url.split('/')[-1] if '/' in url else 'канал'}"
            partner_name = url.split('/')[-1] if '/' in url else "Партнер"
        else:
            title = f"💬 Вступи в {url.split('/')[-1] if '/' in url else 'группу'}"
            partner_name = url.split('/')[-1] if '/' in url else "Партнер"
    
    # Для activity нужно настроить дополнительные параметры
    if task_type == "channel_activity":
        logging.info(f"🔧 Processing channel_activity for {data.get('channel', 'unknown_channel')}")
        
        text = (
            f"💬 <b>Настройка активности в {data.get('channel', 'канале')}</b>\n\n"
            f"⚙️ Настройте параметры задания:\n\n"
            f"💡 По умолчанию:\n"
            f"• 3 комментария\n"
            f"• За 7 дней\n"
            f"• На 2 постах\n"
            f"• 5 капсул награда"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Использовать по умолчанию", callback_data="activity_default")],
            [types.InlineKeyboardButton(text="⚙️ Настроить вручную", callback_data="activity_custom")]
        ])
        
        await state.set_state(TaskCreation.waiting_activity_params)
        try:
            await message.answer(text, reply_markup=keyboard)
            logging.info(f"✅ Activity config menu sent successfully")
        except Exception as e:
            logging.error(f"❌ Failed to send activity config: {e}")
            await message.answer("❌ Ошибка отправки настроек. Попробуйте снова.")
    else:
        # Для обычных заданий сразу выбор награды
        type_name = data.get('type_name', 'ресурс')
        
        text = (
            f"🎁 <b>Выберите награду за {type_name}:</b>\n\n"
            f"📢 Ссылка: {data.get('partner_url', '')}\n"
            f"🎯 Название: {data.get('title', '')}\n\n"
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

# ================== ОБРАБОТЧИКИ ACTIVITY ==================

@router.callback_query(F.data.startswith("activity_"))
async def handle_activity_params(callback: CallbackQuery, state: FSMContext):
    """Обработать параметры активности"""
    if not callback.data or len(callback.data.split("_")) < 2:
        return
    param_type = callback.data.split("_")[1]
    
    if param_type == "default":
        # Использовать параметры по умолчанию
        await state.update_data(
            min_comments=3,
            period_days=7,
            min_posts=2,  # По умолчанию 2 поста
            reward_capsules=5
        )
        
        # Переходим к финализации
        await finalize_activity_task(callback, state)
        
    elif param_type == "custom":
        text = (
            "⚙️ <b>Настройка параметров</b>\n\n"
            "Введите параметры в формате:\n"
            "<code>комментарии дни посты награда</code>\n\n"
            "Например: <code>5 14 3 7</code>\n"
            "• 5 комментариев\n"
            "• За 14 дней\n"
            "• Под 3 постами\n"
            "• 7 капсул награды"
        )
        
        await safe_edit_message(callback, text)
        # Остаемся в waiting_activity_params

@router.message(TaskCreation.waiting_activity_params)
async def process_activity_params(message: types.Message, state: FSMContext):
    """Обработать кастомные параметры активности"""
    try:
        if not message.text:
            await message.answer("❌ Введите параметры в формате: комментарии дни посты награда")
            return
        parts = message.text.strip().split()
        if len(parts) != 4:
            raise ValueError("Неверное количество параметров")
        
        min_comments = int(parts[0])
        period_days = int(parts[1]) 
        min_posts = int(parts[2])
        reward_capsules = int(parts[3])
        
        # Валидация
        if min_comments < 1 or min_comments > 20:
            await message.answer("❌ Количество комментариев должно быть от 1 до 20")
            return
        
        if period_days < 1 or period_days > 30:
            await message.answer("❌ Период должен быть от 1 до 30 дней")
            return
            
        if min_posts < 1 or min_posts > 10:
            await message.answer("❌ Количество постов должно быть от 1 до 10")
            return
        
        if reward_capsules < 1 or reward_capsules > 15:
            await message.answer("❌ Награда должна быть от 1 до 15 капсул")
            return
        
        await state.update_data(
            min_comments=min_comments,
            period_days=period_days,
            min_posts=min_posts,
            reward_capsules=reward_capsules
        )
        
        # Создаем фиктивный callback для finalize_activity_task
        class FakeCallback:
            def __init__(self, user_id):
                self.from_user = type('obj', (object,), {'id': user_id})
                self.message = message
            
            async def answer(self, text="", show_alert=False):
                # Фиктивный async метод
                pass
        
        fake_callback = FakeCallback(message.from_user.id if message.from_user else 0)
        await finalize_activity_task(fake_callback, state)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Используйте:\n"
            "<code>комментарии дни посты награда</code>\n\n"
            "Например: <code>3 7 2 5</code>\n"
            "• 3 комментария\n"
            "• За 7 дней\n"
            "• Под 2 постами\n"
            "• 5 капсул награды"
        )

async def finalize_activity_task(callback, state: FSMContext):
    """Финализировать создание задания активности"""
    data = await state.get_data()
    
    min_comments = data.get('min_comments', 3)
    period_days = data.get('period_days', 7)
    min_posts = data.get('min_posts', 2)  # По умолчанию 2 поста
    reward_capsules = data.get('reward_capsules', 5)
    channel = data.get('channel', '')
    
    # Создаем описание с ясными требованиями
    if min_posts == 1:
        description = f"💬 Оставьте {min_comments} комментариев в канале {channel} за {period_days} дней\n\n⚠️ Важно: Комментарии можно оставлять под одним постом"
    else:
        description = f"💬 Оставьте {min_comments} комментариев под {min_posts} РАЗНЫМИ постами в канале {channel} за {period_days} дней\n\n⚠️ Обязательно: Комментарии должны быть под разными постами!\n📝 Пример: {min_comments//min_posts + (1 if min_comments % min_posts else 0)} комментариев под 1 постом, {min_comments//min_posts} комментариев под 2 постом, и т.д."
    
    # Обновляем title с указанием количества постов
    if min_posts == 1:
        title = f"💬 {min_comments} комментариев в {channel}"
    else:
        title = f"💬 {min_comments} комментариев под {min_posts} постами в {channel}"
    
    # Requirements для channel_activity
    requirements = {
        "channel": channel,
        "min_comments": min_comments,
        "period_days": period_days,
        "min_posts": min_posts,
        "start_date": datetime.now().isoformat()
    }
    
    # Создаем задание в БД
    db = get_db()
    cfg = get_config()
    
    try:
        task_id = db.add_task(
            title=title,
            description=description,
            task_type="channel_activity",
            reward_capsules=reward_capsules,
            partner_name=data.get('partner_name', channel.replace('@', '')),
            partner_url=data.get('partner_url', f"https://t.me/{channel.replace('@', '')}"),
            requirements=json.dumps(requirements),
            expires_at=None,  # Без срока действия
            max_completions=None  # Без ограничений
        )
        
        text = (
            f"✅ <b>Задание создано!</b>\n\n"
            f"🎯 <b>{title}</b>\n\n"
            f"{description}\n\n"
            f"🎁 Награда: {reward_capsules} капсул\n"
            f"🆔 ID: {task_id}"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📢 Уведомить всех", callback_data=f"notify_users_{task_id}")],
            [types.InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_back")]
        ])
        
        # Безопасное редактирование сообщения
        try:
            if callback.message:
                await safe_edit_message(callback, text, reply_markup=keyboard)
        except Exception as e:
            # Если редактирование не удалось, отправляем новое сообщение
            if callback.message:
                await callback.message.answer(text, reply_markup=keyboard)
            await callback.answer("✅ Задание успешно создано!")
        await state.clear()
        
        logging.info(f"✅ Admin {callback.from_user.id} created CHANNEL_ACTIVITY task {task_id}: {channel}")
        
    except Exception as e:
        logging.error(f"❌ Failed to create activity task: {e}")
        error_text = f"❌ Ошибка создания задания: {str(e)}\n\nПопробуйте снова."
        error_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")]
        ])
        try:
            if callback.message:
                await callback.message.edit_text(error_text, reply_markup=error_keyboard)
        except Exception as e:
            # Если редактирование не удалось, отправляем новое сообщение
            if callback.message:
                await callback.message.answer(error_text, reply_markup=error_keyboard)
            await callback.answer("❌ Ошибка создания задания")

@router.callback_query(F.data.startswith("reward_"))
async def select_reward(callback: CallbackQuery, state: FSMContext):
    """Выбрать награду"""
    if not callback.data or len(callback.data.split("_")) < 2:
        return
    reward_data = callback.data.split("_")[1]
    
    if reward_data == "custom":
        try:
            if callback.message:
                await safe_edit_message(callback, "✏️ <b>Введите количество капсул (от 1 до 15):</b>")
        except:
            await callback.answer("Введите количество капсул (от 1 до 15)", show_alert=True)
        return
    
    try:
        reward = int(reward_data)
    except (ValueError, TypeError):
        await callback.answer("❌ Неверный формат награды", show_alert=True)
        return
    
    await finalize_task_creation(callback, state, reward)

@router.message(TaskCreation.waiting_reward)
async def process_custom_reward(message: types.Message, state: FSMContext):
    """Обработать пользовательскую награду"""
    try:
        reward = int(message.text) if message.text else 0
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
        
        async def answer(self, text="", show_alert=False):
            # Фиктивный async метод
            pass
    
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
    task_id = db.add_task(
        title=task_data['title'],
        description=task_data['description'],
        task_type=task_data['task_type'],
        reward_capsules=task_data['reward_capsules'],
        partner_name=task_data.get('partner_name', ''),
        partner_url=task_data.get('partner_url', ''),
        requirements=task_data.get('requirements', ''),
        expires_at=task_data.get('expires_at'),
        max_completions=task_data.get('max_completions')
    )
    
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
            [types.InlineKeyboardButton(text="📢 Уведомить всех", callback_data=f"notify_users_{task_id}")],
            [types.InlineKeyboardButton(text="➕ Создать еще", callback_data="create_task_start")],
            [types.InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_tasks")]
        ])
        
        try:
            await safe_edit_message(callback, success_text, reply_markup=keyboard)
        except Exception as e:
            # Если редактирование не удалось, отправляем новое сообщение
            await callback.message.answer(success_text, reply_markup=keyboard)
            await callback.answer("✅ Задание успешно создано!")
    else:
        error_text = "❌ Ошибка при создании задания"
        if hasattr(callback.message, 'edit_text'):
            await safe_edit_message(callback, error_text)
        else:
            await callback.message.answer(error_text)
    
    await state.clear()

# ================== МАССОВЫЕ УВЕДОМЛЕНИЯ ==================

@router.callback_query(F.data.startswith("notify_users_"))
async def send_task_notification(callback: CallbackQuery):
    """Отправить уведомление о новом задании всем пользователям"""
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
    db = get_db()
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    # Получаем всех пользователей
    users = db.get_all_users()
    if not users:
        await callback.answer("❌ Нет пользователей для уведомления", show_alert=True)
        return
    
    # Определяем эмодзи по типу задания
    if task['task_type'] == 'channel_subscription':
        type_emoji = "📢"
        action_text = "подпишитесь на канал"
    elif task['task_type'] == 'channel_activity':
        type_emoji = "💬"
        action_text = "выполните активность в канале"
    else:
        type_emoji = "👥"
        action_text = "вступите в группу"
    
    # Формируем сообщение уведомления
    notification_text = (
        f"🎉 <b>Новое задание!</b>\n\n"
        f"{type_emoji} <b>{task['title']}</b>\n"
        f"🏢 Партнер: {task['partner_name']}\n"
        f"🎁 Награда: {task['reward_capsules']} капсул\n\n"
        f"💡 {task['description']}\n\n"
        f"⚡ Чтобы {action_text}, нажмите 🎯 Задания в главном меню!"
    )
    
    # Отправляем уведомления
    success_count = 0
    failed_count = 0
    
    for user in users:
        try:
            if callback.bot:
                await callback.bot.send_message(
                    chat_id=user['user_id'],
                    text=notification_text,
                    parse_mode="HTML"
                )
            success_count += 1
        except Exception as e:
            failed_count += 1
            # Не логируем каждую ошибку, чтобы не спамить
    
    # Отчёт о рассылке
    report_text = (
        f"📊 <b>Рассылка завершена!</b>\n\n"
        f"✅ Доставлено: {success_count} пользователей\n"
        f"❌ Не доставлено: {failed_count} пользователей\n\n"
        f"🎯 Задание: {task['title']}"
    )
    
    if callback.message:
        await safe_edit_message(callback, report_text, parse_mode="HTML")
    await callback.answer("📢 Уведомления отправлены!")

# ================== РЕДАКТИРОВАНИЕ ЗАДАНИЙ ==================

@router.callback_query(F.data.startswith("edit_task_"))
async def start_edit_task(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование задания"""
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
    db = get_db()
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    # Сохраняем ID задания в состоянии
    await state.update_data(editing_task_id=task_id)
    
    text = (
        f"✏️ <b>Редактирование задания ID {task_id}</b>\n\n"
        f"🎯 <b>Название:</b> {task['title']}\n"
        f"📝 <b>Описание:</b> {task['description']}\n"
        f"🎁 <b>Награда:</b> {task['reward_capsules']} капсул\n"
        f"🏢 <b>Партнер:</b> {task['partner_name']}\n"
        f"🔗 <b>Ссылка:</b> {task['partner_url']}\n"
        f"📊 <b>Статус:</b> {'Активно' if task['status'] == 'active' else 'Неактивно'}\n\n"
        f"Что хотите изменить?"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📝 Название", callback_data=f"edit_title_{task_id}")],
        [types.InlineKeyboardButton(text="📄 Описание", callback_data=f"edit_description_{task_id}")],
        [types.InlineKeyboardButton(text="🎁 Награду", callback_data=f"edit_reward_{task_id}")],
        [types.InlineKeyboardButton(text="🏢 Партнера", callback_data=f"edit_partner_{task_id}")],
        [types.InlineKeyboardButton(text="🔗 Ссылку", callback_data=f"edit_url_{task_id}")],
        [types.InlineKeyboardButton(text="📊 Статус", callback_data=f"toggle_status_{task_id}")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_list_tasks")]
    ])
    
    if callback.message:
        await safe_edit_message(callback, text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("edit_title_"))
async def edit_task_title(callback: CallbackQuery, state: FSMContext):
    """Редактировать название задания"""
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
    await state.update_data(editing_task_id=task_id, editing_field="title")
    await state.set_state(TaskEditing.waiting_title)
    
    text = "📝 <b>Редактирование названия</b>\n\nВведите новое название задания:"
    if callback.message:
        await safe_edit_message(callback, text)

@router.callback_query(F.data.startswith("edit_description_"))
async def edit_task_description(callback: CallbackQuery, state: FSMContext):
    """Редактировать описание задания"""
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
    await state.update_data(editing_task_id=task_id, editing_field="description")
    await state.set_state(TaskEditing.waiting_description)
    
    text = "📄 <b>Редактирование описания</b>\n\nВведите новое описание задания:"
    if callback.message:
        await safe_edit_message(callback, text)

@router.callback_query(F.data.startswith("edit_reward_"))
async def edit_task_reward(callback: CallbackQuery, state: FSMContext):
    """Редактировать награду задания"""
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
    await state.update_data(editing_task_id=task_id, editing_field="reward_capsules")
    await state.set_state(TaskEditing.waiting_reward)
    
    text = "🎁 <b>Редактирование награды</b>\n\nВведите новое количество капсул (от 1 до 15):"
    if callback.message:
        await safe_edit_message(callback, text)

@router.callback_query(F.data.startswith("toggle_status_"))
async def toggle_task_status(callback: CallbackQuery, state: FSMContext):
    """Переключить статус задания"""
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
    db = get_db()
    task = db.get_task(task_id)
    
    if not task:
        await callback.answer("❌ Задание не найдено", show_alert=True)
        return
    
    new_status = "inactive" if task['status'] == "active" else "active"
    success = db.update_task_status(task_id, new_status)
    
    if success:
        status_text = "активировано" if new_status == "active" else "деактивировано"
        await callback.answer(f"✅ Задание {status_text}!")
        # Возвращаемся к меню редактирования
        await start_edit_task(callback, state)
    else:
        await callback.answer("❌ Ошибка обновления статуса", show_alert=True)

# Обработчики FSM для редактирования

@router.message(TaskEditing.waiting_title)
async def process_title_edit(message: types.Message, state: FSMContext):
    """Обработать новое название"""
    data = await state.get_data()
    task_id = data.get('editing_task_id')
    if not task_id:
        await message.answer("❌ Ошибка: ID задания не найден")
        await state.clear()
        return
    
    db = get_db()
    success = db.update_task_field(task_id, 'title', message.text)
    
    if success:
        await message.answer("✅ Название обновлено!")
    else:
        await message.answer("❌ Ошибка обновления названия")
    
    await state.clear()

@router.message(TaskEditing.waiting_description)
async def process_description_edit(message: types.Message, state: FSMContext):
    """Обработать новое описание"""
    data = await state.get_data()
    task_id = data.get('editing_task_id')
    if not task_id:
        await message.answer("❌ Ошибка: ID задания не найден")
        await state.clear()
        return
    
    db = get_db()
    success = db.update_task_field(task_id, 'description', message.text)
    
    if success:
        await message.answer("✅ Описание обновлено!")
    else:
        await message.answer("❌ Ошибка обновления описания")
    
    await state.clear()

@router.message(TaskEditing.waiting_reward)
async def process_reward_edit(message: types.Message, state: FSMContext):
    """Обработать новую награду"""
    try:
        reward = int(message.text) if message.text else 0
        if reward < 1 or reward > 15:
            await message.answer("❌ Награда должна быть от 1 до 15 капсул")
            return
    except ValueError:
        await message.answer("❌ Введите число от 1 до 15")
        return
    
    data = await state.get_data()
    task_id = data.get('editing_task_id')
    if not task_id:
        await message.answer("❌ Ошибка: ID задания не найден")
        await state.clear()
        return
    
    db = get_db()
    success = db.update_task_field(task_id, 'reward_capsules', reward)
    
    if success:
        await message.answer(f"✅ Награда обновлена на {reward} капсул!")
    else:
        await message.answer("❌ Ошибка обновления награды")
    
    await state.clear()

# ================== ОБЩИЕ ФУНКЦИИ ==================
@router.callback_query(F.data == "tasks_back")
async def tasks_back(callback: CallbackQuery):
    """Вернуться в главное меню заданий"""
    if not callback.from_user or not callback.message:
        return
    
    # Создаем имитацию объекта message с правильным from_user
    class FakeMessage:
        def __init__(self, callback_query):
            self.from_user = callback_query.from_user
            self.message_obj = callback_query.message
            
        async def answer(self, text, reply_markup=None, parse_mode=None):
            if self.message_obj:
                await self.message_obj.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    
    fake_message = FakeMessage(callback)
    await tasks_menu(fake_message)

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
        if callback.message:
            await safe_edit_message(callback, text, reply_markup=keyboard)
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
                text=f"✏️ Редактировать ID {task['id']}", 
                callback_data=f"edit_task_{task['id']}"
            ),
            types.InlineKeyboardButton(
                text=f"🗑️ Удалить ID {task['id']}", 
                callback_data=f"delete_task_{task['id']}"
            )
        ])
    
    keyboard_buttons.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if callback.message:
        await safe_edit_message(callback, text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("delete_task_"))
async def confirm_delete_task(callback: CallbackQuery):
    """Подтверждение удаления задания"""
    if not callback.from_user:
        return
    
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
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
    
    if callback.message:
        await safe_edit_message(callback, text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("confirm_delete_"))
async def execute_delete_task(callback: CallbackQuery):
    """Выполнить удаление задания"""
    if not callback.from_user:
        return
    
    cfg = get_config()
    if callback.from_user.id not in cfg.ADMIN_IDS:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    if not callback.data or len(callback.data.split("_")) < 3:
        return
    try:
        task_id_str = callback.data.split("_")[2]
        task_id = int(task_id_str) if task_id_str else 0
    except (ValueError, IndexError):
        return
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
    
    if callback.message:
        await safe_edit_message(callback, text, reply_markup=keyboard)

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
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")]
        ])
    else:
        text = f"📋 <b>Все задания ({len(tasks)}):</b>\n\n"
        keyboard_buttons = []
        
        active_count = 0
        for task in tasks:
            status_emoji = "✅" if task['status'] == 'active' else "❌"
            # Определяем эмодзи по типу задания
            if task['task_type'] == 'channel_subscription':
                type_emoji = "📢"
            elif task['task_type'] == 'channel_activity':
                type_emoji = "💬"
            else:
                type_emoji = "👥"
            
            if task['status'] == 'active':
                active_count += 1
            
            text += (
                f"{status_emoji} <b>ID {task['id']}</b> {type_emoji} {task['title']}\n"
                f"   🏢 {task['partner_name']}\n"
                f"   👤 Выполнили: {task['current_completions']}\n"
                f"   🎁 {task['reward_capsules']} капсул\n\n"
            )
            
            # Добавляем кнопку редактирования для каждого задания
            keyboard_buttons.append([
                types.InlineKeyboardButton(
                    text=f"✏️ Редактировать ID {task['id']}", 
                    callback_data=f"edit_task_{task['id']}"
                )
            ])
        
        text += f"📊 Активных: {active_count}, Всего: {len(tasks)}"
        
        # Добавляем кнопку "Назад"
        keyboard_buttons.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tasks")])
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if callback.message:
        await safe_edit_message(callback, text, reply_markup=keyboard)