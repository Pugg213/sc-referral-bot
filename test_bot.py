#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности SC Referral Bot
"""
import asyncio
import sqlite3
from datetime import datetime
from app.config import Settings
from app.db import Database
from app.services.captcha import CaptchaService
from app.services.capsules import CapsuleService

def test_database():
    """Тест базы данных"""
    print("🗄️ Тестирование базы данных...")
    
    db = Database("bot.db")
    
    # Проверить таблицы
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Таблицы: {', '.join(tables)}")
        
        # Подсчитать пользователей
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"Пользователей в базе: {user_count}")

def test_config():
    """Тест конфигурации"""
    print("\n⚙️ Тестирование конфигурации...")
    
    cfg = Settings.from_env()
    print(f"Токен бота: {'✅ настроен' if cfg.BOT_TOKEN else '❌ отсутствует'}")
    print(f"ID канала: {cfg.REQUIRED_CHANNEL_ID if cfg.REQUIRED_CHANNEL_ID else '❌ не настроен'}")
    print(f"ID группы: {cfg.REQUIRED_GROUP_ID if cfg.REQUIRED_GROUP_ID else '❌ не настроена'}")
    print(f"Лимит капсул в день: {cfg.DAILY_CAPSULE_LIMIT}")
    print(f"Количество наград в капсулах: {len(cfg.CAPSULE_REWARDS)}")

async def test_services():
    """Тест сервисов"""
    print("\n🛠️ Тестирование сервисов...")
    
    # Тест сервиса капсул
    capsule_service = CapsuleService()
    cfg = Settings.from_env()
    
    # Проверить конфигурацию наград
    errors = capsule_service.validate_rewards_config(cfg.CAPSULE_REWARDS)
    if errors:
        print(f"❌ Ошибки конфигурации капсул: {errors}")
    else:
        print("✅ Конфигурация капсул корректна")
        
        # Симуляция открытия капсул
        rewards = []
        for _ in range(10):
            reward = capsule_service.open_capsule(cfg.CAPSULE_REWARDS)
            if reward:
                rewards.append(reward)
        
        if rewards:
            avg_reward = sum(r.amount for r in rewards) / len(rewards)
            print(f"Среднее значение 10 капсул: {avg_reward:.2f} SC")

def test_bot_status():
    """Проверить статус бота"""
    print("\n🤖 Статус бота:")
    
    try:
        # Проверить логи бота (если доступны)
        with open("bot.log", "r") as f:
            recent_logs = f.readlines()[-5:]
            print("Последние 5 строк логов:")
            for log in recent_logs:
                print(f"  {log.strip()}")
    except FileNotFoundError:
        print("Лог файл не найден")
    
    # Проверить время создания базы данных
    try:
        import os
        db_time = datetime.fromtimestamp(os.path.getmtime("bot.db"))
        print(f"База данных создана: {db_time.strftime('%d.%m.%Y %H:%M:%S')}")
    except FileNotFoundError:
        print("❌ База данных не найдена")

def main():
    """Запустить все тесты"""
    print("🔍 Запуск тестов SC Referral Bot\n")
    
    test_database()
    test_config() 
    asyncio.run(test_services())
    test_bot_status()
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    main()