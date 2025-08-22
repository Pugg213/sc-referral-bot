"""
Клавиатуры для Telegram бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основное меню"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Профиль"),
                KeyboardButton(text="🎁 Открыть капсулу")
            ],
            [
                KeyboardButton(text="👥 Рефералы"),
                KeyboardButton(text="🏆 Топ")
            ],
            [
                KeyboardButton(text="💼 Кошелек"),
                KeyboardButton(text="🎯 Задания")
            ],
            [
                KeyboardButton(text="📅 Чек-ин"),
                KeyboardButton(text="📋 Правила")
            ]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для профиля"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎁 Открыть капсулу", callback_data="open_capsule"),
                InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals")
            ],
            [
                InlineKeyboardButton(text="💼 Кошелек", callback_data="wallet"),
                InlineKeyboardButton(text="🏆 Топ", callback_data="leaderboard")
            ],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
    )

def get_wallet_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для кошелька"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔗 Привязать кошелек", callback_data="link_wallet"),
                InlineKeyboardButton(text="💸 Запросить вывод", callback_data="request_withdrawal")
            ]
        ]
    )

def get_referrals_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для рефералов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 Поделиться ссылкой", callback_data="share_link"),
                InlineKeyboardButton(text="👥 Мои рефералы", callback_data="my_referrals")
            ]
        ]
    )

def get_subscription_keyboard(channel_link: str | None = None, group_link: str | None = None) -> InlineKeyboardMarkup:
    """Клавиатура для проверки подписки"""
    buttons = []
    
    if channel_link:
        buttons.append([InlineKeyboardButton(text="📢 Подписаться на канал", url=channel_link)])
    
    if group_link:
        buttons.append([InlineKeyboardButton(text="💬 Вступить в группу", url=group_link)])
    
    buttons.append([InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_subscription")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_captcha_keyboard(session_id: int, options: list) -> InlineKeyboardMarkup:
    """Клавиатура для капчи"""
    buttons = []
    row = []
    
    for i, option in enumerate(options):
        row.append(InlineKeyboardButton(
            text=str(option), 
            callback_data=f"captcha_{session_id}_{option}"
        ))
        
        # По 3 кнопки в ряд
        if len(row) == 3:
            buttons.append(row)
            row = []
    
    if row:  # Добавить оставшиеся кнопки
        buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Главная админ панель"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="💸 Выплаты", callback_data="admin_payouts")
            ],
            [
                InlineKeyboardButton(text="⚠️ Анти-накрутка", callback_data="admin_risks"),
                InlineKeyboardButton(text="🚫 Пользователи", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="🎯 Управление заданиями", callback_data="admin_tasks")
            ],
            [
                InlineKeyboardButton(text="🔙 Обычное меню", callback_data="admin_exit")
            ]
        ]
    )

def get_admin_stats_keyboard() -> InlineKeyboardMarkup:
    """Меню статистики"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👥 Общая статистика", callback_data="stats_general"),
                InlineKeyboardButton(text="📈 По дням", callback_data="stats_daily")
            ],
            [
                InlineKeyboardButton(text="🎁 Капсулы", callback_data="stats_capsules"),
                InlineKeyboardButton(text="💰 Балансы", callback_data="stats_balances")
            ],
            [
                InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_back")
            ]
        ]
    )

def get_admin_payouts_keyboard() -> InlineKeyboardMarkup:
    """Меню выплат"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Активные запросы", callback_data="payouts_pending"),
                InlineKeyboardButton(text="✅ Завершить запрос", callback_data="payouts_complete")
            ],
            [
                InlineKeyboardButton(text="📄 Экспорт CSV", callback_data="payouts_export"),
                InlineKeyboardButton(text="📜 История", callback_data="payouts_history")
            ],
            [
                InlineKeyboardButton(text="💵 Ручная выплата", callback_data="payouts_manual"),
                InlineKeyboardButton(text="📊 Статистика выплат", callback_data="payouts_stats")
            ],
            [
                InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_back")
            ]
        ]
    )

def get_admin_risks_keyboard() -> InlineKeyboardMarkup:
    """Меню анти-накрутки"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Подозрительные", callback_data="risks_suspicious"),
                InlineKeyboardButton(text="⚠️ Высокий риск", callback_data="risks_high")
            ],
            [
                InlineKeyboardButton(text="📊 Скоринг рисков", callback_data="risks_scores"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="risks_settings")
            ],
            [
                InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_back")
            ]
        ]
    )

def get_admin_users_keyboard() -> InlineKeyboardMarkup:
    """Меню управления пользователями"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="users_search"),
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data="users_ban")
            ],
            [
                InlineKeyboardButton(text="✅ Разблокировать", callback_data="users_unban"),
                InlineKeyboardButton(text="📋 Список банов", callback_data="users_banned")
            ],
            [
                InlineKeyboardButton(text="🔙 Админ панель", callback_data="admin_back")
            ]
        ]
    )

def get_tasks_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для заданий"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Доступные задания", callback_data="available_tasks"),
                InlineKeyboardButton(text="✅ Выполненные", callback_data="completed_tasks")
            ]
        ]
    )

def get_task_action_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с заданием"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнить задание", callback_data=f"complete_task_{task_id}")],
            [InlineKeyboardButton(text="📋 Список заданий", callback_data="available_tasks")]
        ]
    )

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка "Назад" """
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]]
    )

def get_confirm_keyboard(action: str, data: str = "") -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}_{data}"),
                InlineKeyboardButton(text="❌ Нет", callback_data="cancel")
            ]
        ]
    )
