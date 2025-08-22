#!/usr/bin/env python3
"""
Скрипт для восстановления целостности данных в БД после редеплоев
Выполняет полный пересчет всех статистик пользователей
"""

import sqlite3
import logging
from datetime import datetime

def restore_data_integrity():
    """Восстанавливает все статистики пользователей"""
    
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    print("🔧 НАЧИНАЮ ВОССТАНОВЛЕНИЕ ЦЕЛОСТНОСТИ ДАННЫХ...")
    
    # 1. Пересчет рефералов
    print("📊 Пересчитываю рефералы...")
    cursor.execute("""
        UPDATE users SET 
            total_referrals = (
                SELECT COUNT(*) 
                FROM users u2 
                WHERE u2.referrer_id = users.user_id
            ),
            validated_referrals = (
                SELECT COUNT(*) 
                FROM referral_validations rv 
                WHERE rv.referrer_id = users.user_id 
                AND rv.validated = 1
            )
        WHERE user_id IN (
            SELECT DISTINCT referrer_id 
            FROM users 
            WHERE referrer_id IS NOT NULL
        )
    """)
    referrals_updated = cursor.rowcount
    print(f"✅ Обновлено {referrals_updated} пользователей с рефералами")
    
    # 2. Пересчет доходов от капсул
    print("💰 Пересчитываю доходы от капсул...")
    cursor.execute("""
        UPDATE users SET 
            total_earnings = (
                SELECT COALESCE(SUM(sc_amount), 0) 
                FROM capsule_openings co 
                WHERE co.user_id = users.user_id
            ) + (
                SELECT COALESCE(SUM(sc_amount), 0) 
                FROM user_checkins uc 
                WHERE uc.user_id = users.user_id
            )
    """)
    earnings_updated = cursor.rowcount
    print(f"✅ Обновлено {earnings_updated} пользователей с доходами")
    
    # 3. Пересчет балансов
    print("💳 Пересчитываю балансы...")
    cursor.execute("""
        UPDATE users SET 
            pending_balance = total_earnings - paid_balance
    """)
    balances_updated = cursor.rowcount
    print(f"✅ Обновлено {balances_updated} балансов")
    
    # 4. Пересчет капсул
    print("🎁 Пересчитываю капсулы...")
    cursor.execute("""
        UPDATE users SET 
            total_capsules_opened = (
                SELECT COALESCE(COUNT(*), 0) 
                FROM capsule_openings co 
                WHERE co.user_id = users.user_id
            )
    """)
    capsules_updated = cursor.rowcount
    print(f"✅ Обновлено {capsules_updated} счетчиков капсул")
    
    # 5. Исправление subscription_checked
    print("🔒 Проверяю статусы подписки...")
    cursor.execute("""
        UPDATE users SET subscription_checked = 1 
        WHERE subscription_checked = 0 
        AND user_id IN (
            SELECT DISTINCT referrer_id 
            FROM referral_validations 
            WHERE validated = 1
        )
    """)
    subscription_fixed = cursor.rowcount
    print(f"✅ Исправлено {subscription_fixed} статусов подписки")
    
    conn.commit()
    
    # 6. Финальная проверка
    print("\n📋 ФИНАЛЬНАЯ СТАТИСТИКА:")
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE total_referrals > 0")
    users_with_referrals = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_referrals) FROM users")
    total_referrals_system = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(total_earnings) FROM users")
    total_earnings_system = cursor.fetchone()[0] or 0
    
    print(f"👥 Всего пользователей: {total_users}")
    print(f"📈 Пользователей с рефералами: {users_with_referrals}")
    print(f"🔗 Всего рефералов в системе: {total_referrals_system}")
    print(f"💰 Общие доходы системы: {total_earnings_system:.2f} SC")
    
    conn.close()
    print("\n✅ ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
    
    return {
        'users_updated': max(referrals_updated, earnings_updated, balances_updated, capsules_updated),
        'total_users': total_users,
        'users_with_referrals': users_with_referrals,
        'total_referrals': total_referrals_system,
        'total_earnings': total_earnings_system
    }

if __name__ == "__main__":
    result = restore_data_integrity()
    print(f"\n🎯 ИТОГ: Обновлено {result['users_updated']} пользователей")