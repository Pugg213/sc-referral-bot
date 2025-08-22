"""
Mini App handler для добавления кнопки TMA в основной бот
"""
import logging
from aiogram import Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.enums import ChatType

from app.context import get_config

router = Router()

@router.message(F.text == "⭐ Stars Store", F.chat.type == ChatType.PRIVATE)
async def stars_store_handler(message: types.Message):
    """Обработчик кнопки Stars Store - прямой запуск TMA"""
    try:
        # TMA URL - для тестирования используем порт 5001
        import os
        replit_domains = os.getenv('REPLIT_DOMAINS', '')
        if replit_domains:
            domain = replit_domains.split(',')[0]
            # TMA на стандартном порту для compatibility 
            tma_url = f"https://{domain}"
        else:
            # Fallback для локальной разработки
            tma_url = "http://localhost:5000"
        
        # Create Web App button for direct launch
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ Открыть Stars Store",
                    web_app=WebAppInfo(url=tma_url)
                )
            ]
        ])
        
        store_text = """⭐ <b>Telegram Stars Store</b>

🛒 Покупайте Stars через TON блокчейн!

<b>💫 Доступные пакеты:</b>
• 50 Stars - стартовый 
• 100 Stars - популярный
• 250 Stars - выгодный
• 500 Stars - максимальный

<b>🔥 Преимущества:</b>
• Мгновенное зачисление Stars
• Оплата через TON кошелек
• Безопасные транзакции
• Используйте Stars в любых ботах

Нажмите кнопку для открытия магазина!"""
        
        await message.answer(
            store_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Stars store handler error: {e}")
        await message.answer("❌ Ошибка загрузки магазина")

@router.callback_query(F.data == "show_balance")
async def show_balance_callback(callback: types.CallbackQuery):
    """Показать баланс пользователя"""
    try:
        await callback.answer()
        
        from app.context import get_db
        db = get_db()
        user = db.get_user(callback.from_user.id)
        
        if user:
            balance_text = f"""💰 <b>Ваш баланс</b>

💎 SC Токены: {user.get('balance', 0):.2f}
📊 Всего заработано: {user.get('total_earnings', 0):.2f}
🎁 Капсул открыто: {user.get('total_referrals', 0)}
👥 Рефералов: {user.get('validated_referrals', 0)}"""
        else:
            balance_text = "❌ Пользователь не найден"
            
        if callback.message:
            await callback.message.answer(balance_text, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Show balance error: {e}")
        await callback.answer("❌ Ошибка получения баланса", show_alert=True)

@router.callback_query(F.data == "purchase_history")
async def purchase_history_callback(callback: types.CallbackQuery):
    """Показать историю покупок Stars"""
    try:
        await callback.answer()
        
        from app.context import get_db
        db = get_db()
        
        # Simplified purchase history (no database table needed)
        purchases = []  # Empty for now
        
        if purchases:
            history_text = "🛒 <b>История покупок Stars</b>\n\n"
            for product_id, stars, date in purchases:
                history_text += f"📦 {product_id}\n💰 {stars} ⭐ - {date[:10]}\n\n"
        else:
            history_text = "🛒 <b>История покупок пуста</b>\n\nВы еще не совершали покупок Telegram Stars."
            
        if callback.message:
            await callback.message.answer(history_text, parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Purchase history error: {e}")
        await callback.answer("❌ Ошибка получения истории", show_alert=True)