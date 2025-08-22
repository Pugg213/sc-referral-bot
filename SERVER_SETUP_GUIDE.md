# 🚀 SC REFERRAL BOT - ПОЛНАЯ ИНСТРУКЦИЯ ПО УСТАНОВКЕ

## 📋 СИСТЕМНЫЕ ТРЕБОВАНИЯ

### Минимальные требования:
- **OS**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **RAM**: 2GB минимум, 4GB рекомендуется  
- **CPU**: 1 vCore (2 vCore для высокой нагрузки)
- **Диск**: 20GB свободного места
- **Сеть**: Статический IP и домен

### Рекомендуемые VPS провайдеры:
- **DigitalOcean** ($10-20/месяц)
- **Vultr** ($6-12/месяц) 
- **Linode** ($10-20/месяц)
- **Contabo** ($4-8/месяц)

---

## 🔧 ШАГИ УСТАНОВКИ

### 1️⃣ ПОДГОТОВКА СЕРВЕРА

```bash
# Подключение к серверу
ssh root@YOUR_SERVER_IP

# Обновление системы
apt update && apt upgrade -y

# Установка необходимых пакетов
apt install -y python3 python3-pip python3-venv git curl wget nginx certbot python3-certbot-nginx

# Создание пользователя для бота
adduser botuser
usermod -aG sudo botuser
su - botuser

# Создание рабочей директории
mkdir ~/sc-bot && cd ~/sc-bot
```

### 2️⃣ ЗАГРУЗКА И РАСПАКОВКА

```bash
# Загрузка архива (через scp с вашего компьютера)
scp sc-bot-FULL-*.tar.gz botuser@YOUR_SERVER_IP:~/sc-bot/

# ИЛИ через wget если размещен онлайн
# wget https://your-storage.com/sc-bot-FULL-*.tar.gz

# Распаковка
tar -xzf sc-bot-FULL-*.tar.gz
cd sc-bot-FULL-*/

# Проверка содержимого
ls -la
```

### 3️⃣ УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ

```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r server_requirements.txt

# Проверка установки
pip list
```

### 4️⃣ НАСТРОЙКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ

```bash
# Копирование примера конфигурации
cp env_example.txt .env

# Редактирование .env файла
nano .env
```

**Обязательно укажите:**
```env
# Основные настройки
BOT_TOKEN=your_bot_token_from_botfather
WEBHOOK_URL=https://yourdomain.com/webhook
HOST=0.0.0.0
PORT=5000

# Telegram API (получить на https://my.telegram.org/apps)
TG_API_ID=your_api_id
TG_API_HASH=your_api_hash
SESSION_STRING=will_be_generated_later

# База данных
DATABASE_PATH=/home/botuser/sc-bot/bot.db

# Домен
CUSTOM_DOMAIN=yourdomain.com
```

### 5️⃣ СОЗДАНИЕ SESSION_STRING

```bash
# Запуск генератора сессий
python simple_session_generator.py

# Следуйте инструкциям:
# 1. Введите ваш номер телефона (+7XXXXXXXXXX)
# 2. Введите код из Telegram
# 3. Скопируйте SESSION_STRING

# Добавьте SESSION_STRING в .env файл
nano .env
# SESSION_STRING=полученная_строка
```

### 6️⃣ НАСТРОЙКА NGINX

```bash
# Создание конфигурации Nginx
sudo nano /etc/nginx/sites-available/sc-bot
```

**Конфигурация Nginx:**
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Основные запросы к боту
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Увеличиваем таймауты для длительных операций
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Статические файлы TMA
    location /static/ {
        alias /home/botuser/sc-bot/sc-bot-FULL-*/public/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # TMA файлы
    location /tma/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активация сайта
sudo ln -s /etc/nginx/sites-available/sc-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7️⃣ SSL СЕРТИФИКАТ

```bash
# Получение SSL сертификата от Let's Encrypt
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Проверка автообновления
sudo certbot renew --dry-run
```

### 8️⃣ СОЗДАНИЕ SYSTEMD СЕРВИСА

```bash
# Создание файла сервиса
sudo nano /etc/systemd/system/sc-bot.service
```

**Конфигурация сервиса:**
```ini
[Unit]
Description=SC Referral Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=botuser
Group=botuser
WorkingDirectory=/home/botuser/sc-bot/sc-bot-FULL-20250822_XXXXXX
Environment=PATH=/home/botuser/sc-bot/sc-bot-FULL-20250822_XXXXXX/venv/bin
ExecStart=/home/botuser/sc-bot/sc-bot-FULL-20250822_XXXXXX/venv/bin/python start_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Ограничения ресурсов
MemoryLimit=1G
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

```bash
# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable sc-bot
sudo systemctl start sc-bot

# Проверка статуса
sudo systemctl status sc-bot
```

---

## 🚀 ЗАПУСК И ПРОВЕРКА

### Проверка работы:
```bash
# Статус сервиса
sudo systemctl status sc-bot

# Логи в реальном времени
sudo journalctl -u sc-bot -f

# Проверка портов
netstat -tlnp | grep 5000

# Проверка health endpoint
curl -I https://yourdomain.com/health
```

### Если все работает правильно, вы увидите:
```
HTTP/2 200
content-type: application/json
{"status": "healthy", "bot": {...}}
```

---

## 📊 МОНИТОРИНГ И ОБСЛУЖИВАНИЕ

### Управление сервисом:
```bash
sudo systemctl start sc-bot     # Запуск
sudo systemctl stop sc-bot      # Остановка
sudo systemctl restart sc-bot   # Перезапуск
sudo systemctl reload sc-bot    # Перезагрузка конфигурации
```

### Логи и мониторинг:
```bash
# Логи бота
sudo journalctl -u sc-bot -n 100

# Логи Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Использование ресурсов
htop
df -h
free -h
```

### Бэкапы базы данных:
```bash
# Создание бэкапа
cp bot.db bot_backup_$(date +%Y%m%d_%H%M%S).db

# Автоматический бэкап (добавить в crontab)
crontab -e
# Добавить строку:
# 0 2 * * * cp /home/botuser/sc-bot/sc-bot-FULL-*/bot.db /home/botuser/backups/bot_backup_$(date +\%Y\%m\%d).db
```

---

## 🔧 TROUBLESHOOTING

### Проблема: Бот не отвечает
```bash
# Проверить статус
sudo systemctl status sc-bot

# Проверить логи
sudo journalctl -u sc-bot -n 50

# Проверить webhook
curl https://yourdomain.com/webhook
```

### Проблема: SESSION_STRING не работает
```bash
# Пересоздать SESSION_STRING
python simple_session_generator.py

# Обновить .env
nano .env

# Перезапустить бота
sudo systemctl restart sc-bot
```

### Проблема: SSL сертификат
```bash
# Обновить сертификат
sudo certbot renew

# Проверить конфигурацию Nginx
sudo nginx -t
sudo systemctl reload nginx
```

### Проблема: База данных
```bash
# Проверить права доступа
ls -la bot.db

# Проверить целостность
sqlite3 bot.db "PRAGMA integrity_check;"

# Восстановить из бэкапа
cp bot_backup_YYYYMMDD.db bot.db
```

---

## 📈 ОПТИМИЗАЦИЯ ПРОИЗВОДИТЕЛЬНОСТИ

### Настройка системы:
```bash
# Увеличить лимиты файлов
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Оптимизация сети
echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
sysctl -p
```

### Мониторинг производительности:
```bash
# Установка htop для мониторинга
apt install htop

# Мониторинг логов
apt install multitail
multitail /var/log/nginx/access.log /var/log/nginx/error.log
```

---

## 🎯 ФИНАЛЬНАЯ ПРОВЕРКА

После завершения установки проверьте:

1. **✅ Бот отвечает**: Напишите /start в @your_bot
2. **✅ Webhook работает**: `curl https://yourdomain.com/health`
3. **✅ TMA загружается**: Откройте мини-приложение в боте
4. **✅ База данных**: Проверьте регистрацию новых пользователей
5. **✅ Задания**: Проверьте работу системы заданий
6. **✅ SSL**: Проверьте https://yourdomain.com

---

## 📞 ПОДДЕРЖКА

При возникновении проблем:

1. **Проверьте логи**: `sudo journalctl -u sc-bot -f`
2. **Проверьте конфигурацию**: `nginx -t` и настройки .env
3. **Проверьте ресурсы**: `htop`, `df -h`, `free -h`
4. **Перезапустите сервисы**: `sudo systemctl restart sc-bot nginx`

**🎉 Поздравляем! SC Referral Bot готов к работе на вашем сервере!**