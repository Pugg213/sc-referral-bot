"""
Исправленные обработчики команд старта БЕЗ LSP ошибок
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType

from app.context import get_config, get_db
from app.keyboards import get_main_keyboard, get_subscription_keyboard
from app.services.captcha import CaptchaService
from app.utils.subscription import check_user_subscriptions
from app.utils.helpers import extract_referrer_id, format_user_mention

router = Router()

class OnboardingStates(StatesGroup):
    captcha = State()
    subscription_check = State()

@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start_command(message: types.Message, state: FSMContext):
    """Команда /start с онбордингом"""
    if not message.from_user:
        return
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    cfg = get_config()
    db = get_db()
    
    # Извлечь ID реферера из deeplink
    referrer_id = extract_referrer_id(message.text or "")
    logging.info(f"Start command processing - User: {user_id}, Command text: '{message.text}', Extracted referrer: {referrer_id}")
    
    # Проверить, существует ли пользователь
    user = db.get_user(user_id)
    
    if not user:
        # Новый пользователь - создать и начать онбординг
        logging.info(f"Creating new user: {user_id}, username: {username}, referrer: {referrer_id}")
        if db.create_user(user_id, username, first_name, referrer_id or 0):
            logging.info(f"✅ New user registered successfully: {user_id} (referred by: {referrer_id})")
            
            # Проверим, что реферер действительно записался
            created_user = db.get_user(user_id)
            if created_user:
                logging.info(f"✅ User verification: {created_user.get('referrer_id', 'No referrer field')}")
            else:
                logging.error(f"❌ User not found after creation: {user_id}")
                
            # Начать с капчи
            captcha_service = CaptchaService()
            session_id, captcha_text, keyboard = await captcha_service.generate_captcha(user_id)
            
            await state.update_data(captcha_session_id=session_id)
            await state.set_state(OnboardingStates.captcha)
            
            welcome_text = (
                f"🎉 <b>Добро пожаловать в SC Referral Bot!</b>\n\n"
                f"👋 Привет, {format_user_mention(first_name or 'Пользователь', username or '')}!\n\n"
                f"🎁 Тебя ждут капсулы с SC наградами!\n"
                f"👥 Приглашай друзей и получай бонусы!\n\n"
                f"📢 <b>Присоединяйся к нашему сообществу:</b>\n"
                f"🔗 Канал: https://t.me/just_a_simple_coin\n"
                f"💬 Чат: https://t.me/simplecoin_chatSC\n\n"
                f"🔐 Сначала пройди проверку безопасности:\n"
                f"{captcha_text}"
            )
            
            try:
                await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Welcome message send error: {e}")
                # Fallback: отправить простое сообщение без клавиатуры
                try:
                    await message.answer("🎉 Добро пожаловать в SC Referral Bot! Пройдите капчу для продолжения.")
                except Exception as e2:
                    logging.error(f"Fallback welcome message failed: {e2}")
        else:
            await message.answer("❌ Ошибка создания аккаунта. Попробуйте позже.")
    else:
        # Существующий пользователь - показать главное меню
        try:
            await show_main_menu(message)
        except Exception as e:
            logging.error(f"Error showing main menu for existing user {user_id}: {e}")
            # Отправить простое приветствие если основное меню не работает
            try:
                await message.answer("👋 Добро пожаловать обратно!", reply_markup=get_main_keyboard())
            except Exception as e2:
                logging.error(f"Failed to send fallback message: {e2}")

@router.callback_query(F.data.startswith("captcha_"))
async def handle_captcha(callback: types.CallbackQuery, state: FSMContext):
    """Обработка ответа на капчу"""
    if not callback.data or not callback.from_user:
        return
    try:
        parts = callback.data.split("_")
        session_id = int(parts[1])
        user_answer = int(parts[2])
        
        captcha_service = CaptchaService()
        is_correct, solve_time = await captcha_service.check_captcha(session_id, user_answer)
        
        if is_correct:
            # Капча решена правильно
            cfg = get_config()
            db = get_db()
            
            # Вычислить и сохранить captcha_score
            captcha_score = captcha_service.calculate_captcha_score(solve_time, cfg.RISK_THRESHOLDS)
            db.update_user_scores(callback.from_user.id, captcha_score=captcha_score)
            
            # Перейти к проверке подписки
            await callback.answer("✅ Проверка пройдена!")
            # Проверяем что message доступно
            if callback.message and hasattr(callback.message, 'answer'):
                # Безопасное приведение типа
                from aiogram.types import Message
                if isinstance(callback.message, Message):
                    await start_subscription_check(callback.message, state)
        else:
            await callback.answer("❌ Неправильный ответ! Попробуйте еще раз.", show_alert=True)
            
    except (ValueError, IndexError):
        await callback.answer("❌ Ошибка обработки капчи.", show_alert=True)

async def start_subscription_check(message: types.Message, state: FSMContext):
    """Начать проверку подписки"""
    cfg = get_config()
    
    keyboard = get_subscription_keyboard(cfg.CHANNEL_LINK, cfg.GROUP_LINK)
    
    # Формируем ссылки для отображения в тексте
    if cfg.CHANNEL_LINK:
        channel_link_text = f'<a href="{cfg.CHANNEL_LINK}">📢 Канал Simple Coin</a>'
    else:
        channel_link_text = "📢 Канал Simple Coin"
    
    if cfg.GROUP_LINK:
        group_link_text = f'<a href="{cfg.GROUP_LINK}">💬 Группа Simple Coin</a>'
    else:
        group_link_text = "💬 Группа Simple Coin"
    
    text = (
        "📋 <b>Для продолжения подпишитесь на Simple Coin:</b>\n\n"
        "<b>Обязательно:</b> подпишитесь на канал с новостями\n"
        f"🔗 {channel_link_text}\n\n"
        "<b>По желанию:</b> вступите в группу сообщества\n"
        f"🔗 {group_link_text}\n\n"
        "💡 <i>После подписки нажмите кнопку \"Проверить подписку\"</i>"
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(OnboardingStates.subscription_check)

@router.callback_query(F.data == "check_subscription")
async def handle_subscription_check(callback: types.CallbackQuery, state: FSMContext):
    """КРИТИЧЕСКИЙ HANDLER: Проверка подписки пользователя"""
    if not callback.from_user:
        return
    
    user_id = callback.from_user.id
    cfg = get_config()
    db = get_db()
    
    await callback.answer("🔍 Проверяю подписку...")
    
    try:
        # ИСПРАВЛЕНО: Добавлен параметр bot
        from app.utils.subscription import check_user_subscriptions
        
        # Получаем bot из callback (с проверкой)
        bot = callback.bot
        if not bot:
            await callback.answer("❌ Ошибка системы", show_alert=True)
            return
            
        is_subscribed = await check_user_subscriptions(
            bot, user_id, cfg.REQUIRED_CHANNEL_ID, cfg.REQUIRED_GROUP_ID
        )
        
        if is_subscribed:
            # ИСПРАВЛЕНО: Обновляем subscription_checked в БД
            db.update_subscription_status(user_id, True)
            
            try:
                from aiogram.types import Message
                if callback.message and isinstance(callback.message, Message):
                    await callback.message.edit_text(
                        "✅ <b>Подписка подтверждена!</b>\n\n"
                        "🎉 Добро пожаловать в Simple Coin!\n"
                        "🎁 Теперь ты можешь открывать капсулы и зарабатывать SC!"
                    )
            except Exception:
                pass  # Message might be inaccessible
            
            await state.clear()
            # Показать главное меню
            if callback.message and hasattr(callback.message, 'answer'):
                from aiogram.types import Message
                if isinstance(callback.message, Message):
                    await show_main_menu(callback.message)
                
        else:
            try:
                from aiogram.types import Message
                if callback.message and isinstance(callback.message, Message):
                    await callback.message.edit_text(
                        "❌ <b>Подписка не найдена</b>\n\n"
                        "📋 Убедитесь что вы:\n"
                        "• Подписались на канал Simple Coin\n"
                        "• Вступили в группу (если требуется)\n\n"
                        "💡 После подписки нажмите кнопку еще раз",
                        reply_markup=get_subscription_keyboard(cfg.CHANNEL_LINK, cfg.GROUP_LINK)
                    )
            except Exception:
                pass  # Message might be inaccessible
            
    except Exception as e:
        logging.error(f"Subscription check error for user {user_id}: {e}")
        try:
            from aiogram.types import Message
            if callback.message and isinstance(callback.message, Message):
                await callback.message.edit_text(
                    "❌ Ошибка проверки подписки. Попробуйте позже.",
                    reply_markup=get_subscription_keyboard(cfg.CHANNEL_LINK, cfg.GROUP_LINK)
                )
        except Exception:
            pass  # Message might be inaccessible




async def show_main_menu(message: types.Message):
    """Показать главное меню"""
    try:
        # Проверяем что message и chat доступны
        if not message or not message.chat:
            logging.warning("show_main_menu: message or chat is None")
            return
            
        text = (
            "🏠 <b>Главное меню</b>\n\n"
            "Добро пожаловать в SC Referral Bot! Используйте кнопки ниже для навигации:\n\n"
            "🎁 <b>Капсулы</b> - открывайте и получайте награды\n"
            "👥 <b>Рефералы</b> - приглашайте друзей\n"
            "💰 <b>Баланс</b> - проверьте свои SC токены\n"
            "👤 <b>Профиль</b> - ваша статистика\n"
            "📋 <b>Правила</b> - как использовать бота\n"
            "🎯 <b>Задания</b> - выполняйте и получайте бонусы"
        )
        
        keyboard = get_main_keyboard()
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"show_main_menu error: {e}")
        # Не пытаемся отправить сообщение если chat недоступен