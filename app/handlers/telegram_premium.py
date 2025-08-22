"""
Telegram Premium Handler - покупка Telegram Premium через Rhombis API
"""
import logging
import json
from aiogram import Router, types, F
from aiogram.filters import Command

from app.context import get_config, get_db
from app.services.rhombis_stars_api import get_rhombis_stars_api, RHOMBIS_STARS_PRODUCTS

logger = logging.getLogger(__name__)
router = Router()

@router.message(F.web_app_data)
async def handle_telegram_premium_purchase(message: types.Message):
    """Обработка покупки Telegram Premium через TMA"""
    if not message.from_user or not message.web_app_data:
        return
    
    try:
        # Парсим данные из Web App
        data = json.loads(message.web_app_data.data)
        
        if data.get("action") != "buy_telegram_premium":
            return
            
        user_id = message.from_user.id
        plan_id = data.get("plan_id")
        stars_price = data.get("stars_price")
        user_data = data.get("user_data", {})
        
        # Находим план в конфигурации
        telegram_premium_plan = None
        for plan in RHOMBIS_STARS_PRODUCTS["telegram_premium"]:
            if plan["id"] == plan_id:
                telegram_premium_plan = plan
                break
        
        if not telegram_premium_plan:
            await message.answer("❌ План не найден")
            return
        
        # Создаем покупку через Rhombis API
        rhombis_api = get_rhombis_stars_api()
        
        try:
            purchase_response = await rhombis_api.purchase_telegram_premium({
                "telegram_id": user_id,
                "username": user_data.get("username", ""),
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "duration_months": telegram_premium_plan["duration_months"],
                "stars_price": stars_price,
                "features": telegram_premium_plan["features"]
            })
            
            if purchase_response.get("success"):
                # Успешная покупка
                success_text = (
                    f"🎉 <b>Telegram Premium активирован!</b>\n\n"
                    f"📦 <b>План:</b> {telegram_premium_plan['title']}\n"
                    f"⏰ <b>Срок:</b> {telegram_premium_plan['duration_months']} мес.\n"
                    f"⭐ <b>Потрачено:</b> {stars_price} Stars\n\n"
                    f"🚀 <b>Ваши новые возможности:</b>\n"
                )
                
                for feature in telegram_premium_plan["features"][:4]:  # Показываем первые 4 функции
                    success_text += f"✅ {feature}\n"
                
                success_text += f"\n💫 Наслаждайтесь Telegram Premium!"
                
                await message.answer(success_text, parse_mode="HTML")
                
            else:
                error_msg = purchase_response.get("error", "Unknown error")
                await message.answer(f"❌ Ошибка активации Premium: {error_msg}")
                
        except Exception as e:
            logger.error(f"Rhombis API error for Telegram Premium: {e}")
            await message.answer("❌ Временная ошибка сервиса. Попробуйте позже.")
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON data from Web App")
        await message.answer("❌ Ошибка обработки данных")
    except Exception as e:
        logger.error(f"Telegram Premium purchase error: {e}")
        await message.answer("❌ Произошла ошибка при покупке Premium")

@router.message(Command("telegram_premium"))
async def show_telegram_premium_options(message: types.Message):
    """Показать опции Telegram Premium"""
    if not message.from_user:
        return
    
    premium_text = (
        f"📱 <b>Telegram Premium</b>\n\n"
        f"Получите расширенные возможности Telegram:\n\n"
        f"🔥 <b>Основные функции:</b>\n"
        f"• Загрузка файлов до 2GB\n"
        f"• Быстрая скорость загрузки\n"
        f"• Преобразование голоса в текст\n"
        f"• Расширенные стикеры и реакции\n"
        f"• Без рекламы в публичных каналах\n"
        f"• Приоритетная поддержка\n\n"
        f"💫 <b>Доступные планы:</b>\n\n"
    )
    
    for plan in RHOMBIS_STARS_PRODUCTS["telegram_premium"]:
        popular_mark = " 🔥" if plan.get("popular") else ""
        premium_text += (
            f"📦 <b>{plan['title']}</b>{popular_mark}\n"
            f"💫 {plan['stars_price']} Stars\n"
            f"⏰ {plan['duration_months']} мес.\n\n"
        )
    
    premium_text += f"🌟 Используйте /webapp для покупки через удобный интерфейс"
    
    await message.answer(premium_text, parse_mode="HTML")

@router.message(Command("webapp"))
async def show_webapp_button(message: types.Message):
    """Показать кнопку для открытия Web App"""
    if not message.from_user:
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text="🌟 Открыть SC Store", 
            web_app=types.WebAppInfo(url="https://your-replit-url.replit.app/simple_tma.html")
        )]
    ])
    
    await message.answer(
        "🌟 <b>SC Store - Premium Services</b>\n\n"
        "Купите Telegram Premium и другие премиум услуги через удобный интерфейс:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )