
import asyncio
import sys
import os
sys.path.append('.')

# Инициализируем контекст первым делом
from temp_config import get_working_settings
from app.db import Database
from app.context import set_context

# Инициализация
cfg = get_working_settings()
db = Database()
db.initialize()
set_context(cfg, db)

from app.context import get_config, get_db
from app.handlers.admin_final import is_admin
from app.services.capsules import CapsuleService

async def test_all_systems():
    print('🧪 ТЕСТИРОВАНИЕ ВСЕХ СИСТЕМ')
    print('=' * 27)
    
    # Тест конфигурации
    try:
        cfg = get_config()
        print('✅ Конфигурация загружена')
        print(f'   BOT_TOKEN: {len(cfg.BOT_TOKEN)} символов')
        print(f'   ADMIN_IDS: {cfg.ADMIN_IDS}')
    except Exception as e:
        print(f'❌ Конфигурация: {e}')
    
    # Тест базы данных
    try:
        db = get_db()
        total_users = db.execute_query('SELECT COUNT(*) FROM users')[0][0]
        print(f'✅ База данных: {total_users} пользователей')
    except Exception as e:
        print(f'❌ База данных: {e}')
    
    # Тест админ функций
    try:
        is_admin_result = is_admin(545921)
        print(f'✅ Админ проверка: {is_admin_result}')
    except Exception as e:
        print(f'❌ Админ функции: {e}')
    
    # Тест капсульной системы
    try:
        from app.config import CapsuleReward
        rewards = [
            CapsuleReward(amount=0.5, type="SC", probability=0.4),
            CapsuleReward(amount=1.0, type="SC", probability=0.3),
            CapsuleReward(amount=2.0, type="SC", probability=0.2),
        ]
        capsule_service = CapsuleService()
        reward = capsule_service.open_capsule(rewards)
        print(f'✅ Капсульная система: {reward}')
    except Exception as e:
        print(f'❌ Капсульная система: {e}')

if __name__ == '__main__':
    asyncio.run(test_all_systems())
