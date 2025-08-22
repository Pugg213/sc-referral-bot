# 🤖 SC Referral Bot

**Полнофункциональный Telegram бот с реферальной системой, капсулами и Telegram Mini App**

## 🚀 Особенности

- ✅ **Реферальная система** с многоуровневой проверкой
- ✅ **Система капсул** с вероятностными наградами
- ✅ **Проверка комментариев** через Telethon API
- ✅ **Telegram Mini App** (TMA) для покупки Stars
- ✅ **TON Connect** интеграция для платежей
- ✅ **Антифрод система** с капчей и скорингом
- ✅ **Админ панель** с полным управлением
- ✅ **База данных** SQLite с 12 таблицами

## 📊 Статистика

- **40+ Python модулей** для backend логики
- **12 React компонентов** для TMA интерфейса  
- **63 пользователя** в базе данных
- **95% функциональность** (проверка комментариев требует SESSION_STRING)

## 🛠️ Установка

### Быстрая установка:

```bash
git clone https://github.com/Pugg213/sc-referral-bot.git
cd sc-referral-bot
pip install -r server_requirements.txt
cp .env.example .env
nano .env  # настроить переменные
python simple_session_generator.py  # создать SESSION_STRING
python start_server.py  # запустить бота
```

### Подробная инструкция:

См. файл `SERVER_SETUP_GUIDE.md` для полной инструкции по развертыванию.

## 🔧 Конфигурация

Создайте файл `.env` с необходимыми переменными:

```env
BOT_TOKEN=your_bot_token
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash
SESSION_STRING=your_session_string
WEBHOOK_URL=https://yourdomain.com/webhook
```

## 🎯 Структура проекта

```
├── app/                    # Backend код
│   ├── handlers/          # Обработчики команд
│   ├── services/          # Бизнес логика
│   ├── middleware/        # Промежуточное ПО
│   └── utils/            # Утилиты
├── src/                   # React TMA
├── public/               # Статические файлы
├── main.py              # Главный файл бота
├── start_server.py      # Запуск сервера
└── bot.db              # База данных
```

## 🚀 Готово к деплою!

Проект полностью готов к развертыванию на любом сервере с поддержкой Python 3.11+