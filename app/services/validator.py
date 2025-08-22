"""
Сервис валидации рефералов в фоновом режиме
"""
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot

from app.context import get_config, get_db
from app.services.scoring import RiskScorer

async def validator_loop(bot: Bot):
    """Основной цикл валидации рефералов"""
    logging.info("Validator loop started")
    
    while True:
        try:
            await validate_pending_referrals(bot)
        except Exception as e:
            logging.error(f"Error in validator loop: {e}")
        
        # Пауза между итерациями (30 секунд для тестирования)
        await asyncio.sleep(30)

async def validate_pending_referrals(bot: Bot):
    """Валидация ожидающих рефералов"""
    db = get_db()
    cfg = get_config()
    
    # Получить рефералов для валидации
    pending_validations = db.get_pending_validations(100)
    
    if not pending_validations:
        return
    
    risk_scorer = RiskScorer()
    
    for validation in pending_validations:
        try:
            await validate_single_referral(bot, validation, risk_scorer, cfg)
            
            # Небольшая пауза между проверками
            await asyncio.sleep(1)
            
        except Exception as e:
            logging.error(f"Error validating referral {validation['id']}: {e}")

async def validate_single_referral(bot: Bot, validation: dict, risk_scorer: RiskScorer, cfg):
    """Валидация одного реферала"""
    db = get_db()
    
    referred_id = validation['referred_id']
    validation_id = validation['id']
    
    # Проверить, прошел ли пользователь карантин
    quarantine_time = cfg.RISK_THRESHOLDS.quarantine_hours
    validation_date = datetime.fromisoformat(validation['validation_date'])
    quarantine_end = validation_date + timedelta(hours=quarantine_time)
    
    # Логируем для отладки
    logging.info(f"Checking referral {referred_id}: quarantine ends at {quarantine_end}, now is {datetime.now()}")
    
    if datetime.now() < quarantine_end:
        # Еще в карантине
        logging.info(f"Referral {referred_id} still in quarantine")
        return
    
    # Получить данные о пользователе
    referred_user = db.get_user(referred_id)
    if not referred_user:
        # Пользователь не найден - отклонить
        risk_flags = "user_not_found"
        db.validate_referral(validation_id, False, risk_flags)
        logging.info(f"Referral {referred_id} rejected: user not found")
        return
    
    # Проверить подписку пользователя
    if not referred_user['subscription_checked']:
        # Пользователь не прошел проверку подписки - отклонить
        risk_flags = "no_subscription_check"
        db.validate_referral(validation_id, False, risk_flags)
        logging.info(f"Referral {referred_id} rejected: no subscription check")
        return
    
    # Вычислить риск-скор
    user_data = {
        'user_id': referred_id,
        'registration_date': validation['registration_date'],
        'captcha_score': validation['captcha_score'],
        'subscription_checked': validation['subscription_checked']
    }
    
    risk_score = await risk_scorer.calculate_risk_score(bot, user_data, cfg.RISK_THRESHOLDS)
    
    # Обновить риск-скор в базе
    db.update_user_scores(referred_id, risk_score=risk_score)
    
    # Принять решение о валидации
    risk_threshold = 0.7  # Порог риска для отклонения
    
    if risk_score < risk_threshold:
        # Низкий риск - принять реферала
        db.validate_referral(validation_id, True)
        logging.info(f"Referral {referred_id} validated (risk score: {risk_score:.2f})")
        
        # Уведомить реферера о подтверждении
        try:
            referrer_id = validation['referrer_id']
            await bot.send_message(
                referrer_id,
                f"✅ <b>Реферал подтвержден!</b>\n\n"
                f"👤 Новый участник прошел проверку\n"
                f"🎁 Вы получили 1.0 SC за приглашение!"
            )
        except:
            pass  # Реферер мог заблокировать бота
            
    else:
        # Высокий риск - отклонить
        risk_flags = f"high_risk_score_{risk_score:.2f}"
        db.validate_referral(validation_id, False, risk_flags)
        logging.info(f"Referral {referred_id} rejected: high risk score {risk_score:.2f}")
        
        # Уведомить реферера об отклонении
        try:
            referrer_id = validation['referrer_id']
            await bot.send_message(
                referrer_id,
                f"❌ <b>Реферал не подтвержден</b>\n\n"
                f"👤 Приглашенный пользователь не прошел проверку безопасности\n"
                f"⚠️ Убедитесь, что вы приглашаете только реальных людей"
            )
        except:
            pass

async def check_daily_limits(user_id: int) -> bool:
    """Проверить дневные лимиты рефералов"""
    db = get_db()
    cfg = get_config()
    
    # Подсчитать рефералов за последние 24 часа
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as refs_today
            FROM referral_validations rv
            JOIN users u ON rv.referred_id = u.user_id
            WHERE rv.referrer_id = ? 
            AND u.registration_date >= datetime('now', '-1 day')
        """, (user_id,))
        
        result = cursor.fetchone()
        refs_today = result['refs_today'] if result else 0
    
    return refs_today < cfg.RISK_THRESHOLDS.max_refs_per_day

async def check_hourly_limits(user_id: int) -> bool:
    """Проверить часовые лимиты рефералов"""
    db = get_db()
    cfg = get_config()
    
    # Подсчитать рефералов за последний час
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as refs_hour
            FROM referral_validations rv
            JOIN users u ON rv.referred_id = u.user_id
            WHERE rv.referrer_id = ? 
            AND u.registration_date >= datetime('now', '-1 hour')
        """, (user_id,))
        
        result = cursor.fetchone()
        refs_hour = result['refs_hour'] if result else 0
    
    return refs_hour < cfg.RISK_THRESHOLDS.max_refs_per_hour
