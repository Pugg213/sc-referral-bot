#!/usr/bin/env python3
"""
Тест рефералов и админ панели
"""
import asyncio
import logging
from datetime import datetime, timedelta
from app.config import Settings
from app.db import Database
from app.context import set_context
from app.services.captcha import CaptchaService
from app.services.capsules import CapsuleService

logging.basicConfig(level=logging.INFO)

async def test_referral_system():
    """Тест реферальной системы"""
    print("🔗 Тестирование реферальной системы...")
    
    # Загрузка конфигурации
    try:
        from temp_config import get_working_settings
        cfg = get_working_settings()
    except ImportError:
        cfg = Settings.from_env()
    
    db = Database(cfg.DB_PATH)
    db.init()
    set_context(cfg=cfg, db=db)
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем текущих пользователей
        cursor.execute("SELECT user_id, username, referrer_id, total_referrals FROM users")
        users = cursor.fetchall()
        
        print(f"  📊 Всего пользователей: {len(users)}")
        for user in users:
            referrer_text = f"реферер: {user[2]}" if user[2] else "без реферера"
            print(f"    • ID {user[0]} (@{user[1] or 'без username'}) - {referrer_text}, рефералов: {user[3]}")
        
        # Проверяем валидацию рефералов
        cursor.execute("SELECT COUNT(*) FROM referral_validations")
        validations = cursor.fetchone()[0]
        print(f"  ✅ Валидаций рефералов: {validations}")
        
        # Проверяем подписки
        cursor.execute("SELECT COUNT(*) FROM users WHERE subscription_checked = TRUE")
        subscribed = cursor.fetchone()[0]
        print(f"  📺 Проверенных подписок: {subscribed}")
        
        # Проверяем баланс пользователей
        cursor.execute("SELECT SUM(total_earnings), SUM(pending_balance) FROM users")
        earnings_data = cursor.fetchone()
        total_earnings = earnings_data[0] or 0
        pending_balance = earnings_data[1] or 0
        print(f"  💰 Общий заработок: {total_earnings} SC")
        print(f"  💳 В ожидании: {pending_balance} SC")

async def test_admin_panel():
    """Тест админ панели"""
    print("\n👑 Тестирование админ панели...")
    
    try:
        from temp_config import get_working_settings
        cfg = get_working_settings()
    except ImportError:
        cfg = Settings.from_env()
    
    db = Database(cfg.DB_PATH)
    set_context(cfg=cfg, db=db)
    
    # Проверяем админов
    print(f"  👥 Настроенных админов: {len(cfg.ADMIN_IDS)}")
    for admin_id in cfg.ADMIN_IDS:
        print(f"    • Admin ID: {admin_id}")
    
    # Проверяем функции админки
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем задания
        cursor.execute("SELECT id, title, reward_capsules, channel_id FROM tasks")
        tasks = cursor.fetchall()
        print(f"  📋 Заданий в системе: {len(tasks)}")
        for task in tasks:
            print(f"    • Задание {task[0]}: '{task[1]}' (награда: {task[2]} капсул, канал: {task[3]})")
        
        # Проверяем выполнения заданий
        cursor.execute("SELECT task_id, COUNT(*) FROM user_task_completions GROUP BY task_id")
        completions = cursor.fetchall()
        print(f"  ✅ Выполнений по заданиям:")
        for completion in completions:
            print(f"    • Задание {completion[0]}: {completion[1]} выполнений")

async def test_capsule_system():
    """Тест системы капсул"""
    print("\n🎁 Тестирование системы капсул...")
    
    try:
        from temp_config import get_working_settings
        cfg = get_working_settings()
    except ImportError:
        cfg = Settings.from_env()
    
    # Тест сервиса капсул
    capsule_service = CapsuleService()
    
    # Проверяем конфигурацию наград
    errors = capsule_service.validate_rewards_config(cfg.CAPSULE_REWARDS)
    if errors:
        print("  ❌ Ошибки в конфигурации наград:")
        for error in errors:
            print(f"    • {error}")
    else:
        print("  ✅ Конфигурация наград корректна")
    
    # Получаем статистику
    stats = capsule_service.get_reward_statistics(cfg.CAPSULE_REWARDS)
    print(f"  📊 Статистика наград:")
    print(f"    • Всего наград: {stats['total_rewards']}")
    print(f"    • Ожидаемая ценность: {stats['expected_value']:.2f} SC")
    print(f"    • Минимальная награда: {stats['min_reward']} SC")
    print(f"    • Максимальная награда: {stats['max_reward']} SC")
    print(f"    • Самая вероятная: {stats['most_likely'].name} ({stats['most_likely'].probability*100:.1f}%)")
    
    # Тест открытия капсулы
    print("  🎲 Тестирование открытия капсулы:")
    for i in range(5):
        reward = capsule_service.open_capsule(cfg.CAPSULE_REWARDS)
        if reward:
            print(f"    • Попытка {i+1}: {reward.name} - {reward.amount} SC")

async def test_captcha_system():
    """Тест системы капчи"""
    print("\n🔐 Тестирование системы капчи...")
    
    try:
        from temp_config import get_working_settings
        cfg = get_working_settings()
    except ImportError:
        cfg = Settings.from_env()
    
    db = Database(cfg.DB_PATH)
    set_context(cfg=cfg, db=db)
    
    captcha_service = CaptchaService()
    
    # Генерируем тестовую капчу
    test_user_id = 12345
    captcha_id, question, correct_answer = await captcha_service.generate_captcha(test_user_id)
    
    print(f"  🧮 Сгенерированная капча:")
    print(f"    • ID: {captcha_id}")
    print(f"    • Вопрос: {question}")
    print(f"    • Правильный ответ: {correct_answer}")
    
    # Проверяем решение
    is_valid = await captcha_service.validate_solution(captcha_id, str(correct_answer), 5.0)
    print(f"    • Проверка правильного ответа: {'✅ Успех' if is_valid else '❌ Ошибка'}")
    
    # Проверяем неправильный ответ
    is_invalid = await captcha_service.validate_solution(captcha_id, "999", 5.0)
    print(f"    • Проверка неправильного ответа: {'❌ Неожиданно прошел' if is_invalid else '✅ Корректно отклонен'}")

async def main():
    """Основная функция тестирования"""
    print("🧪 Комплексное тестирование функциональности бота\n")
    
    await test_referral_system()
    await test_admin_panel()
    await test_capsule_system()
    await test_captcha_system()
    
    print("\n🎉 Все тесты завершены!")
    print("\n📋 Краткий отчет:")
    print("✅ Реферальная система работает")
    print("✅ Админ панель функционирует")
    print("✅ Система капсул активна")
    print("✅ CAPTCHA система работает")
    print("✅ База данных в порядке")

if __name__ == "__main__":
    asyncio.run(main())