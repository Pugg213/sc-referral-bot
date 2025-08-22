# 🚀 SC Referral Bot - Инструкция по деплою на сторонний сервер

## 📋 Требования
- Python 3.11+
- Ubuntu/Debian сервер
- Минимум 1GB RAM
- 10GB свободного места

## 🔧 Установка на сервер

### 1️⃣ Подготовка сервера
```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить Python и зависимости
sudo apt install python3 python3-pip python3-venv git curl -y

# Создать директорию для бота
mkdir ~/sc-bot && cd ~/sc-bot
```

### 2️⃣ Загрузка проекта
```bash
# Скопировать файлы проекта на сервер
# (через scp, git clone, или другим способом)

# Например через git:
git clone your-repository-url .

# Или загрузить архив проекта
```

### 3️⃣ Установка зависимостей
```bash
# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r server_requirements.txt
```

### 4️⃣ Настройка переменных окружения
```bash
# Скопировать пример конфигурации
cp env_example.txt .env

# Отредактировать .env файл
nano .env
```

**Обязательно укажите:**
- `BOT_TOKEN` - токен вашего бота от @BotFather
- `TG_API_ID` - получить на https://my.telegram.org/apps
- `TG_API_HASH` - получить на https://my.telegram.org/apps  
- `SESSION_STRING` - создать через simple_session_generator.py
- `WEBHOOK_URL` - https://yourdomain.com/webhook

### 5️⃣ Создание SESSION_STRING
```bash
# Запустить генератор сессий
python simple_session_generator.py

# Следовать инструкциям:
# 1. Ввести номер телефона
# 2. Ввести код из Telegram
# 3. Скопировать SESSION_STRING в .env
```

### 6️⃣ Настройка веб-сервера (Nginx)
```bash
# Установить Nginx
sudo apt install nginx -y

# Создать конфигурацию
sudo nano /etc/nginx/sites-available/sc-bot
```

**Конфигурация Nginx:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активировать сайт
sudo ln -s /etc/nginx/sites-available/sc-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7️⃣ SSL сертификат (Let's Encrypt)
```bash
# Установить Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получить SSL сертификат
sudo certbot --nginx -d yourdomain.com
```

### 8️⃣ Создание systemd сервиса
```bash
# Создать сервис
sudo nano /etc/systemd/system/sc-bot.service
```

**Конфигурация сервиса:**
```ini
[Unit]
Description=SC Referral Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/sc-bot
Environment=PATH=/home/ubuntu/sc-bot/venv/bin
ExecStart=/home/ubuntu/sc-bot/venv/bin/python start_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Активировать сервис
sudo systemctl daemon-reload
sudo systemctl enable sc-bot
sudo systemctl start sc-bot

# Проверить статус
sudo systemctl status sc-bot
```

## 🚀 Запуск

### Ручной запуск (для тестирования)
```bash
cd ~/sc-bot
source venv/bin/activate
python start_server.py
```

### Автоматический запуск через systemd
```bash
sudo systemctl start sc-bot    # Запуск
sudo systemctl stop sc-bot     # Остановка
sudo systemctl restart sc-bot  # Перезапуск
sudo systemctl status sc-bot   # Статус
```

## 📊 Мониторинг

### Логи бота
```bash
sudo journalctl -u sc-bot -f     # Просмотр логов в реальном времени
sudo journalctl -u sc-bot -n 100 # Последние 100 строк
```

### Логи Nginx
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Проверка здоровья
```bash
curl http://localhost:5000/health
curl https://yourdomain.com/health
```

## 🔧 Docker (альтернативный способ)

### Сборка и запуск через Docker
```bash
# Собрать образ
docker build -t sc-bot .

# Запустить контейнер
docker run -d \
  --name sc-bot \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  sc-bot

# Проверить логи
docker logs -f sc-bot
```

## 🛠️ Troubleshooting

### Проблемы с SESSION_STRING
```bash
# Пересоздать SESSION_STRING
python simple_session_generator.py
# Обновить в .env и перезапустить бота
```

### Проблемы с webhook
```bash
# Проверить доступность
curl -I https://yourdomain.com/webhook

# Проверить логи Telegram webhook
# В логах должно быть: "✅ Webhook set successfully"
```

### Проблемы с базой данных
```bash
# Проверить файл базы данных
ls -la bot.db

# Создать backup
cp bot.db bot.db.backup
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи бота: `sudo journalctl -u sc-bot -f`
2. Проверьте логи Nginx: `sudo tail -f /var/log/nginx/error.log`
3. Убедитесь что все переменные окружения заданы правильно
4. Проверьте доступность домена и SSL сертификата

**Успешного деплоя! 🚀**