"""
Основные обработчики команд пользователей - исправленная версия
"""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from datetime import datetime
from aiogram.enums import ChatType

from app.context import get_config, get_db
from app.keyboards import get_main_keyboard, get_back_keyboard, get_profile_keyboard, get_referrals_keyboard
from app.services.capsules import CapsuleService
from app.utils.helpers import format_user_mention, format_balance

router = Router()

@router.message(F.text == "👤 Профиль", F.chat.type == ChatType.PRIVATE)
@router.message(Command("me"), F.chat.type == ChatType.PRIVATE)
async def profile_command(message: types.Message):
    """Показать профиль пользователя"""
    if not message.from_user:
        return
    user_id = message.from_user.id
    db = get_db()
    cfg = get_config()
    
    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        return
    
    if not user['subscription_checked']:
        await message.answer("❌ Сначала пройдите проверку подписки с помощью /check")
        return
    
    # Генерация реферальной ссылки
    if not message.bot:
        return
    bot_info = await message.bot.get_me()
    if not bot_info or not bot_info.username:
        return
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    # Статус бана
    ban_status = "🚫 Заблокирован" if user['banned'] else "✅ Активен"
    ban_reason = f"\nПричина: {user['ban_reason']}" if user['banned'] and user['ban_reason'] else ""
    
    # Информация о кошельке
    wallet_info = user['wallet_address'] if user['wallet_address'] else "Не указан"
    
    profile_text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Имя: {format_user_mention(user['first_name'], user['username'])}\n"
        f"📅 Регистрация: {user['registration_date'][:10] if user['registration_date'] else 'Неизвестно'}\n"
        f"📊 Статус: {ban_status}{ban_reason}\n\n"
        
        f"💰 <b>Баланс SC:</b>\n"
        f"💳 Доступно: {format_balance(user['balance'])}\n"
        f"✅ Выплачено: {format_balance(user['paid_balance'])}\n"
        f"📈 Всего заработано: {format_balance(user['total_earnings'])}\n\n"
        
        f"👥 <b>Рефералы:</b>\n"
        f"📝 Всего приглашено: {user['total_referrals']}\n"
        f"✅ Подтверждено: {user['validated_referrals']}\n\n"
        
        f"🎁 <b>Капсулы:</b>\n"
        f"📦 Открыто всего: {user['total_capsules_opened']}\n"
        f"🗓 Сегодня: {user['daily_capsules_opened']}/{cfg.DAILY_CAPSULE_LIMIT + (user['validated_referrals'] or 0) + (user.get('bonus_capsules', 0) or 0)}\n\n"
        
        f"💼 <b>Кошелек TON:</b> <code>{wallet_info}</code>\n\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>"
    )
    
    await message.answer(profile_text, reply_markup=get_profile_keyboard())

@router.message(F.text == "🎁 Открыть капсулу", F.chat.type == ChatType.PRIVATE)
@router.message(Command("open"), F.chat.type == ChatType.PRIVATE)
@router.callback_query(F.data == "open_capsule")
async def open_capsule_command(message_or_callback):
    """Открыть капсулу - работает и с сообщениями, и с callback"""
    # Определяем тип входящего объекта
    if hasattr(message_or_callback, 'from_user'):
        user = message_or_callback.from_user
        message = message_or_callback
        callback = None
    else:
        user = message_or_callback.from_user
        message = message_or_callback.message
        callback = message_or_callback
        
    if not user:
        return
    user_id = user.id
    db = get_db()
    cfg = get_config()
    
    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        return
    
    if not user['subscription_checked']:
        await message.answer("❌ Сначала пройдите проверку подписки с помощью /check")
        return
    
    if user['banned']:
        await message.answer("🚫 Вы заблокированы и не можете открывать капсулы.")
        return
    
    # Проверить карантин
    if db.is_in_quarantine(user_id):
        await message.answer("⏰ Ваш аккаунт находится в карантине. Попробуйте позже.")
        return
    
    # Проверить доступные капсулы (базовые + бонусные)
    from app.services.special_rewards import SpecialRewardService
    special_service = SpecialRewardService()
    available_capsules = special_service.get_available_capsules(user_id)
    
    if available_capsules <= 0:
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
        
        if callback:
            await callback.answer(limit_text, show_alert=True)
        else:
            await message.answer(limit_text)
        return
    
    # Открыть капсулу
    capsule_service = CapsuleService()
    reward = capsule_service.open_capsule(cfg.CAPSULE_REWARDS)
    
    if reward:
        # Записать открытие
        db.record_capsule_opening(user_id, reward.name, reward.amount)
        
        # Если использована бонусная капсула, уменьшить их количество
        bonus_capsules = user.get('bonus_capsules', 0) or 0
        if bonus_capsules > 0:
            special_service.use_bonus_capsule(user_id)
        
        # Обработать специальную награду
        reward_result = special_service.process_special_reward(user_id, reward.name, reward.amount)
        
        # Получить обновленные данные
        updated_user = db.get_user(user_id)
        remaining_capsules = special_service.get_available_capsules(user_id)
        
        # Показать результат
        message_text = (
            f"{reward_result['emoji']} <b>Капсула открыта!</b>\n\n"
            f"{reward_result['message']}\n\n"
        )
        
        if not reward_result['special'] and updated_user:
            message_text += f"💰 Ваш баланс: {format_balance(updated_user['balance'])} SC\n"
        
        message_text += f"📦 Осталось капсул: {remaining_capsules}"
        
        # Показать активные эффекты
        luck_multiplier = special_service.get_luck_multiplier(user_id)
        if luck_multiplier > 1.0:
            message_text += f"\n🍀 Активна удача x{luck_multiplier}!"
        
        if updated_user and updated_user.get('bonus_capsules', 0) > 0:
            message_text += f"\n🎁 Бонусных капсул: {updated_user['bonus_capsules']}"
        
        await message.answer(message_text)
        
        logging.info(f"User {user_id} opened capsule: {reward.name} ({reward.amount})")
    else:
        await message.answer("❌ Ошибка при открытии капсулы. Попробуйте позже.")

@router.message(F.text == "👥 Рефералы")
async def referrals_command(message: types.Message):
    """Информация о рефералах"""
    if not message.from_user:
        return
    user_id = message.from_user.id
    db = get_db()
    
    user = db.get_user(user_id)
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        return
    
    # Генерация реферальной ссылки
    if not message.bot:
        return
    bot_info = await message.bot.get_me()
    if not bot_info or not bot_info.username:
        return
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    referral_text = (
        f"👥 <b>Реферальная система</b>\n\n"
        f"📊 <b>Ваша статистика:</b>\n"
        f"📝 Всего приглашено: {user['total_referrals']}\n"
        f"✅ Подтверждено: {user['validated_referrals']}\n"
        f"⏳ На проверке: {user['total_referrals'] - user['validated_referrals']}\n\n"
        
        f"🎁 <b>Как это работает:</b>\n"
        f"• Приглашайте друзей по вашей ссылке\n"
        f"• Каждый подтвержденный реферал = бонусы\n"
        f"• Рефералы проходят проверку на подлинность\n\n"
        
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"📤 Поделитесь этой ссылкой с друзьями!"
    )
    
    await message.answer(referral_text)

@router.message(F.text == "🏆 Топ")
@router.message(Command("top"))
async def top_command(message: types.Message):
    """Показать лидерборд"""
    db = get_db()
    
    top_users = db.get_top_users(10)
    
    if not top_users:
        await message.answer("📊 Пока нет данных для лидерборда.")
        return
    
    leaderboard_text = "🏆 <b>Топ пользователей по заработку</b>\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, user in enumerate(top_users, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        username = user['username'] if user['username'] else user['first_name']
        earnings = format_balance(user['total_earnings'])
        
        leaderboard_text += f"{medal} {username}: {earnings} SC\n"
    
    await message.answer(leaderboard_text)

@router.message(Command("wallet"), F.chat.type == ChatType.PRIVATE)
async def wallet_command(message: types.Message):
    """Команда настройки кошелька"""
    if not message.from_user:
        return
    
    # Извлечь адрес из команды
    command_parts = message.text.split() if message.text else []
    if len(command_parts) > 1:
        # Пользователь указал адрес кошелька
        wallet_address = " ".join(command_parts[1:])
        
        # Улучшенная валидация адреса TON
        if len(wallet_address) < 10:
            await message.answer(
                "❌ <b>Адрес слишком короткий!</b>\n\n"
                "TON адрес должен содержать минимум 10 символов.\n"
                "Пример: <code>/wallet UQD2NmD_lH5f_VN2...</code>"
            )
            return
            
        # Проверка на допустимые символы для TON адреса
        allowed_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
        if not all(c in allowed_chars for c in wallet_address):
            await message.answer(
                "❌ <b>Недопустимые символы в адресе!</b>\n\n"
                "TON адрес может содержать только:\n"
                "• Латинские буквы (A-Z, a-z)\n"
                "• Цифры (0-9)\n"
                "• Символы - и _\n\n"
                "Пример: <code>/wallet UQD2NmD_lH5f_VN2...</code>"
            )
            return
        
        # Проверить регистрацию пользователя
        user_id = message.from_user.id
        db = get_db()
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start")
            return
            
        if not user['subscription_checked']:
            await message.answer("❌ Сначала пройдите проверку подписки с помощью /check")
            return
        
        # Сохранить адрес
        try:
            # Используем прямое обновление через SQL
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET wallet_address = ? WHERE user_id = ?", (wallet_address, user_id))
                if cursor.rowcount == 0:
                    await message.answer("❌ Пользователь не найден в базе данных.")
                    return
                conn.commit()
                
            await message.answer(
                f"✅ <b>Кошелек успешно сохранен!</b>\n\n"
                f"💼 Адрес: <code>{wallet_address}</code>\n\n"
                f"💡 Теперь вы сможете получать выплаты на этот адрес.\n\n"
                f"📋 <b>Важно:</b> Убедитесь, что адрес правильный!\n"
                f"Неправильный адрес может привести к потере средств."
            )
        except Exception as e:
            logging.error(f"Error saving wallet for user {user_id}: {e}")
            await message.answer("❌ Ошибка при сохранении кошелька. Попробуйте позже.")
    else:
        # Показать текущий кошелек и инструкции
        user_id = message.from_user.id
        db = get_db()
        user = db.get_user(user_id)
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Используйте /start")
            return
        
        current_wallet = user['wallet_address'] if user['wallet_address'] else "Не указан"
        
        await message.answer(
            f"💼 <b>Настройка кошелька TON</b>\n\n"
            f"Текущий адрес: <code>{current_wallet}</code>\n\n"
            f"📝 <b>Как изменить:</b>\n"
            f"Отправьте команду с адресом:\n"
            f"<code>/wallet ВАШ_АДРЕС_TON</code>\n\n"
            f"💡 Пример:\n"
            f"<code>/wallet UQD2NmD_lH5f_VN2b_6h...</code>"
        )

@router.message(Command("check"))
async def check_subscription_command(message: types.Message):
    """Повторная проверка подписки"""
    if not message.from_user:
        return
    
    user_id = message.from_user.id
    cfg = get_config()
    db = get_db()
    
    if not message.bot:
        return
    
    try:
        # Проверить подписку на канал
        if cfg.REQUIRED_CHANNEL_ID:
            channel_member = await message.bot.get_chat_member(cfg.REQUIRED_CHANNEL_ID, user_id)
            if channel_member.status in ['left', 'kicked']:
                channel_link = cfg.CHANNEL_LINK if cfg.CHANNEL_LINK else f"https://t.me/c/{str(cfg.REQUIRED_CHANNEL_ID)[4:]}"
                await message.answer(
                    f"❌ Вы не подписаны на канал Simple Coin!\n\n"
                    f"📢 <b>Канал Simple Coin:</b>\n"
                    f"🔗 {channel_link}\n\n"
                    f"После подписки снова используйте /check"
                )
                return
        
        # Проверить участие в группе
        if cfg.REQUIRED_GROUP_ID:
            group_member = await message.bot.get_chat_member(cfg.REQUIRED_GROUP_ID, user_id)
            if group_member.status in ['left', 'kicked']:
                group_link = cfg.GROUP_LINK if cfg.GROUP_LINK else f"https://t.me/c/{str(cfg.REQUIRED_GROUP_ID)[4:]}"
                await message.answer(
                    f"❌ Вы не состоите в группе Simple Coin!\n\n"
                    f"💬 <b>Группа Simple Coin:</b>\n"
                    f"🔗 {group_link}\n\n"
                    f"После вступления снова используйте /check"
                )
                return
        
        # Обновить статус подписки
        db.update_subscription_status(user_id, True)
        
        await message.answer(
            f"✅ <b>Проверка пройдена!</b>\n\n"
            f"Теперь вы можете пользоваться всеми функциями бота."
        )
        
    except Exception as e:
        logging.error(f"Subscription check error: {e}")
        await message.answer("❌ Ошибка при проверке подписки. Попробуйте позже.")