"""
Обработчики команд кошелька и выводов
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.context import get_config, get_db
from app.keyboards import get_main_keyboard
from app.utils.helpers import format_balance

router = Router()

class WalletStates(StatesGroup):
    waiting_for_wallet = State()
    waiting_for_amount = State()

@router.message(Command("wallet"))
async def wallet_command(message: types.Message, state: FSMContext):
    """Команда для привязки кошелька"""
    if not message.from_user or not message.text:
        return
        
    db = get_db()
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return
    
    if not user['subscription_checked']:
        await message.answer("❌ Сначала пройдите проверку подписки через /start")
        return
    
    args = message.text.split()[1:]
    
    if args:
        # Пользователь указал адрес кошелька в команде
        wallet_address = args[0]
        await save_wallet(message, wallet_address)
    else:
        # Запрашиваем адрес кошелька
        if user['wallet_address']:
            await message.answer(
                f"💼 <b>Ваш текущий кошелек:</b>\n"
                f"<code>{user['wallet_address']}</code>\n\n"
                f"Отправьте новый адрес TON кошелька для замены:"
            )
        else:
            await message.answer(
                "💼 <b>Привязка кошелька</b>\n\n"
                "Отправьте адрес вашего TON кошелька:\n"
                "Пример: <code>UQD4FPq-TD7Yay6F4j-s8zr-YvdWBYkkL2xNrqjW6UQKWqqK</code>"
            )
        
        await state.set_state(WalletStates.waiting_for_wallet)

async def save_wallet(message: types.Message, wallet_address: str):
    """Сохранить адрес кошелька"""
    # Базовая валидация TON адреса
    if not wallet_address or len(wallet_address) < 48:
        await message.answer("❌ Неверный формат адреса TON кошелька")
        return
    
    if not message.from_user:
        return
        
    db = get_db()
    db.update_wallet(message.from_user.id, wallet_address)
    
    await message.answer(
        f"✅ <b>Кошелек успешно привязан!</b>\n\n"
        f"💼 Адрес: <code>{wallet_address}</code>\n\n"
        f"Теперь вы можете запросить вывод средств командой /withdraw"
    )

@router.message(WalletStates.waiting_for_wallet)
async def process_wallet(message: types.Message, state: FSMContext):
    """Обработка адреса кошелька"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте адрес кошелька")
        return
    await save_wallet(message, message.text.strip())
    await state.clear()

@router.message(Command("withdraw"))
async def withdraw_command(message: types.Message, state: FSMContext):
    """Команда запроса на вывод"""
    db = get_db()
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return
    
    if not user['subscription_checked']:
        await message.answer("❌ Сначала пройдите проверку подписки")
        return
    
    if not user['wallet_address']:
        await message.answer(
            "❌ <b>Кошелек не привязан</b>\n\n"
            "Сначала привяжите TON кошелек командой /wallet"
        )
        return
    
    if user['pending_balance'] <= 0:
        await message.answer(
            f"❌ <b>Недостаточно средств</b>\n\n"
            f"Ваш баланс: {format_balance(user['pending_balance'])} SC\n"
            f"Откройте капсулы или пригласите друзей для заработка!"
        )
        return
    
    args = message.text.split()[1:]
    
    if args:
        # Пользователь указал сумму в команде
        try:
            amount = float(args[0])
            await process_withdraw_request(message, amount, user)
        except ValueError:
            await message.answer("❌ Неверная сумма для вывода")
    else:
        # Запрашиваем сумму
        await message.answer(
            f"💰 <b>Запрос на вывод</b>\n\n"
            f"Доступно к выводу: {format_balance(user['pending_balance'])} SC\n"
            f"Кошелек: <code>{user['wallet_address']}</code>\n\n"
            f"Введите сумму для вывода:"
        )
        await state.set_state(WalletStates.waiting_for_amount)

@router.message(WalletStates.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    """Обработка суммы для вывода"""
    try:
        amount = float(message.text.strip())
        db = get_db()
        user = db.get_user(message.from_user.id)
        await process_withdraw_request(message, amount, user)
    except ValueError:
        await message.answer("❌ Введите корректную сумму")
        return
    
    await state.clear()

async def process_withdraw_request(message: types.Message, amount: float, user: dict):
    """Обработать запрос на вывод"""
    if amount <= 0:
        await message.answer("❌ Сумма должна быть больше 0")
        return
    
    if amount > user['pending_balance']:
        await message.answer(
            f"❌ <b>Недостаточно средств</b>\n\n"
            f"Запрошено: {format_balance(amount)} SC\n"
            f"Доступно: {format_balance(user['pending_balance'])} SC"
        )
        return
    
    # Минимальная сумма для вывода (временно снижена для тестирования)
    min_withdraw = 5.0
    if amount < min_withdraw:
        await message.answer(
            f"❌ <b>Минимальная сумма для вывода</b>\n\n"
            f"Минимум: {format_balance(min_withdraw)} SC\n"
            f"Запрошено: {format_balance(amount)} SC\n\n"
            f"💡 Продолжайте открывать капсулы и приглашать друзей!"
        )
        return
    
    # Создать запрос на вывод
    db = get_db()
    request_id = db.create_withdrawal_request(message.from_user.id, amount)
    
    if request_id:
        await message.answer(
            f"✅ <b>Запрос на вывод создан!</b>\n\n"
            f"💰 Сумма: {format_balance(amount)} SC\n"
            f"💼 Кошелек: <code>{user['wallet_address']}</code>\n"
            f"🆔 ID запроса: {request_id}\n\n"
            f"Ваш запрос обрабатывается администратором.\n"
            f"После выплаты баланс будет автоматически обновлен."
        )
        
        # Уведомление админов (если включено)
        cfg = get_config()
        if not getattr(cfg, 'DISABLE_ADMIN_NOTIFICATIONS', False):
            admin_text = (
                f"🔔 <b>Новый запрос на вывод</b>\n\n"
                f"👤 Пользователь: {user['first_name']} (@{user['username'] or 'без username'})\n"
                f"💰 Сумма: {format_balance(amount)} SC\n"
                f"🆔 ID запроса: {request_id}\n\n"
                f"Проверьте /withdrawal_requests"
            )
            
            # Отправляем уведомления админам (через контекст бота)
            try:
                bot = message.bot
                for admin_id in cfg.ADMIN_IDS:
                    try:
                        await bot.send_message(admin_id, admin_text)
                    except Exception:
                        pass
            except Exception:
                pass
    else:
        await message.answer("❌ Ошибка создания запроса. Попробуйте позже.")

# ОТКЛЮЧЕН - ДУБЛИРОВАНИЕ с navigation_production.py
# @router.message(F.text == "💼 Кошелек")
async def wallet_menu(message: types.Message):
    """Меню кошелька"""
    db = get_db()
    user = db.get_user(message.from_user.id)
    
    if not user:
        await message.answer("❌ Сначала зарегистрируйтесь через /start")
        return
    
    wallet_text = f"💼 <b>Ваш кошелек</b>\n\n"
    
    if user['wallet_address']:
        wallet_text += f"📱 TON адрес:\n<code>{user['wallet_address']}</code>\n\n"
    else:
        wallet_text += f"❌ Кошелек не привязан\n\n"
    
    wallet_text += (
        f"💰 <b>Баланс:</b>\n"
        f"⏳ К выводу: {format_balance(user['pending_balance'])} SC\n"
        f"✅ Выплачено: {format_balance(user['paid_balance'])} SC\n"
        f"💎 Всего заработано: {format_balance(user['total_earnings'])} SC\n\n"
    )
    
    # Проверить активные запросы на вывод
    active_requests = db.get_user_withdrawal_requests(message.from_user.id)
    if active_requests:
        wallet_text += f"📋 <b>Активные запросы:</b>\n"
        for req in active_requests:
            wallet_text += f"• {format_balance(req['amount'])} SC (#{req['id']})\n"
        wallet_text += "\n"
    
    wallet_text += (
        f"<b>Команды:</b>\n"
        f"/wallet - привязать/изменить кошелек\n"
        f"/withdraw - запросить вывод средств"
    )
    
    await message.answer(wallet_text)