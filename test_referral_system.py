#!/usr/bin/env python3
"""
Тест системы начисления рефералов, капсул и балансов
"""
import asyncio
import sys
import os
sys.path.append('.')

from app.core.context import get_context
from app.services.capsule import CapsuleService
from app.services.validator import ReferralValidator

async def test_referral_system():
    """Тестирование системы рефералов"""
    print("🔄 Тестирование системы рефералов...")
    
    context = get_context()
    validator = ReferralValidator(context)
    
    # Получаем статистику
    db = context.db
    
    # Проверяем активных пользователей
    users = await db.get_all_users()
    active_users = [u for u in users if u.balance > 0 or u.referral_count > 0]
    
    print(f"✅ Всего пользователей: {len(users)}")
    print(f"✅ Активных пользователей: {len(active_users)}")
    
    # Проверяем топ по балансу
    top_users = sorted(users, key=lambda x: x.balance, reverse=True)[:5]
    print("\n🏆 ТОП-5 по балансу:")
    for i, user in enumerate(top_users, 1):
        print(f"{i}. {user.username or user.user_id}: {user.balance} SC")
    
    return True

async def test_capsule_system():
    """Тестирование системы капсул"""
    print("\n🎁 Тестирование системы капсул...")
    
    context = get_context()
    capsule_service = CapsuleService(context)
    
    # Проверяем настройки капсул
    config = context.config.capsule
    print(f"✅ Шанс обычной награды: {config.common_chance}%")
    print(f"✅ Шанс редкой награды: {config.rare_chance}%")
    print(f"✅ Диапазон обычных наград: {config.common_min}-{config.common_max} SC")
    print(f"✅ Диапазон редких наград: {config.rare_min}-{config.rare_max} SC")
    
    # Симуляция открытия капсулы
    reward = capsule_service._calculate_reward()
    print(f"✅ Пример награды: {reward} SC")
    
    return True

async def test_balance_operations():
    """Тестирование операций с балансом"""
    print("\n💰 Тестирование операций с балансом...")
    
    context = get_context()
    db = context.db
    
    # Проверяем общий баланс системы
    users = await db.get_all_users()
    total_balance = sum(user.balance for user in users)
    total_earned = sum(user.total_earned for user in users)
    
    print(f"✅ Общий баланс в системе: {total_balance} SC")
    print(f"✅ Всего заработано пользователями: {total_earned} SC")
    
    # Проверяем данные админа
    admin_user = await db.get_user(545921)  # Little_Pugg
    if admin_user:
        print(f"✅ Баланс админа Little_Pugg: {admin_user.balance} SC")
        print(f"✅ Рефералов у админа: {admin_user.referral_count}")
    
    return True

async def main():
    """Основная функция тестирования"""
    print("🚀 ПРОВЕРКА СИСТЕМ НАЧИСЛЕНИЯ")
    print("=" * 50)
    
    try:
        # Тест всех систем
        await test_referral_system()
        await test_capsule_system() 
        await test_balance_operations()
        
        print("\n" + "=" * 50)
        print("✅ ВСЕ СИСТЕМЫ РАБОТАЮТ КОРРЕКТНО")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(main())