#!/bin/bash

# 🚀 АВТОМАТИЧЕСКАЯ УСТАНОВКА SC REFERRAL BOT НА СЕРВЕР
# Версия: 2.0
# Совместимость: Ubuntu 20.04+, Debian 11+, CentOS 8+

set -e  # Остановка при ошибке

echo "🚀 ЗАПУСК АВТОМАТИЧЕСКОЙ УСТАНОВКИ SC REFERRAL BOT"
echo "================================================="

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Проверка ОС
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        print_error "Не удалось определить операционную систему"
        exit 1
    fi
    print_info "Обнаружена ОС: $OS $VER"
}

# Установка зависимостей для Ubuntu/Debian
install_deps_debian() {
    print_info "Установка зависимостей для Ubuntu/Debian..."
    
    sudo apt update
    sudo apt upgrade -y
    
    # Основные пакеты
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget \
        nginx \
        htop \
        nano \
        unzip \
        build-essential \
        libssl-dev \
        libffi-dev
    
    # Node.js
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    print_status "Зависимости установлены"
}

# Установка зависимостей для CentOS/RHEL
install_deps_centos() {
    print_info "Установка зависимостей для CentOS/RHEL..."
    
    sudo yum update -y
    
    # EPEL репозиторий
    sudo yum install -y epel-release
    
    # Основные пакеты
    sudo yum install -y \
        python3 \
        python3-pip \
        python3-devel \
        git \
        curl \
        wget \
        nginx \
        htop \
        nano \
        unzip \
        gcc \
        gcc-c++ \
        make \
        openssl-devel \
        libffi-devel
    
    # Node.js
    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
    sudo yum install -y nodejs
    
    print_status "Зависимости установлены"
}

# Создание пользователя для бота
create_bot_user() {
    BOT_USER="scbot"
    
    if id "$BOT_USER" &>/dev/null; then
        print_warning "Пользователь $BOT_USER уже существует"
    else
        print_info "Создание пользователя $BOT_USER..."
        sudo useradd -m -s /bin/bash $BOT_USER
        print_status "Пользователь $BOT_USER создан"
    fi
    
    # Добавляем текущего пользователя в группу scbot для доступа
    sudo usermod -a -G $BOT_USER $USER
}

# Клонирование репозитория
clone_repository() {
    BOT_HOME="/home/scbot/sc-referral-bot"
    
    print_info "Клонирование репозитория SC Referral Bot..."
    
    # Удаляем старую директорию если есть
    sudo rm -rf $BOT_HOME
    
    # Клонируем как root, затем меняем владельца
    sudo git clone https://github.com/Pugg213/sc-referral-bot.git $BOT_HOME
    sudo chown -R scbot:scbot $BOT_HOME
    
    print_status "Репозиторий склонирован в $BOT_HOME"
}

# Установка Python зависимостей
install_python_deps() {
    print_info "Установка Python зависимостей..."
    
    cd /home/scbot/sc-referral-bot
    
    # Создаем виртуальное окружение
    sudo -u scbot python3 -m venv venv
    
    # Устанавливаем зависимости
    sudo -u scbot bash -c "source venv/bin/activate && pip install --upgrade pip"
    sudo -u scbot bash -c "source venv/bin/activate && pip install -r requirements.txt"
    
    # Установка дополнительных зависимостей
    sudo -u scbot bash -c "source venv/bin/activate && pip install python-dotenv telethon aiohttp"
    
    print_status "Python зависимости установлены"
}

# Установка Node.js зависимостей
install_node_deps() {
    print_info "Установка Node.js зависимостей..."
    
    cd /home/scbot/sc-referral-bot
    
    # Устанавливаем npm зависимости
    sudo -u scbot npm install
    
    print_status "Node.js зависимости установлены"
}

# Создание конфигурационного файла
create_env_file() {
    print_info "Создание файла конфигурации..."
    
    ENV_FILE="/home/scbot/sc-referral-bot/.env"
    
    # Создаем .env файл с шаблоном
    sudo -u scbot tee $ENV_FILE > /dev/null << 'EOF'
# 🤖 TELEGRAM BOT CONFIGURATION
BOT_TOKEN=your_bot_token_here

# 📱 TELEGRAM API (получить на my.telegram.org)
TG_API_ID=your_api_id_here
TG_API_HASH=your_api_hash_here

# 🔑 SESSION STRING (создать через генератор)
SESSION_STRING=your_session_string_here

# 📢 КАНАЛЫ И ГРУППЫ
REQUIRED_CHANNEL_ID=-1001234567890
REQUIRED_GROUP_ID=-1001234567890
CHANNEL_LINK=https://t.me/+your_channel_link
GROUP_LINK=https://t.me/+your_group_link

# 👑 АДМИНИСТРАТОРЫ (через запятую)
ADMIN_IDS=123456789,987654321

# 🌐 WEBHOOK НАСТРОЙКИ
WEBHOOK_DOMAIN=https://your-domain.com
WEBHOOK_PORT=5000

# 💾 DATABASE
DB_PATH=bot.db

# 🎁 RHOMBIS API (опционально)
RHOMBIS_API_KEY=your_rhombis_key
RHOMBIS_WEBHOOK_SECRET=your_webhook_secret

# 🔗 TON BLOCKCHAIN
TON_TESTNET=false
EOF

    print_status "Конфигурационный файл создан: $ENV_FILE"
    print_warning "ОБЯЗАТЕЛЬНО отредактируйте файл $ENV_FILE перед запуском!"
}

# Создание генератора SESSION_STRING
create_session_generator() {
    print_info "Создание генератора SESSION_STRING..."
    
    GENERATOR_FILE="/home/scbot/sc-referral-bot/create_session.py"
    
    sudo -u scbot tee $GENERATOR_FILE > /dev/null << 'EOF'
#!/usr/bin/env python3
"""
🔐 Генератор SESSION_STRING для SC Referral Bot
"""

import asyncio
import sys
from telethon import TelegramClient

def print_header():
    print("🔐 ГЕНЕРАТОР SESSION_STRING ДЛЯ SC REFERRAL BOT")
    print("=" * 50)
    print()

def get_api_credentials():
    print("📱 Получите API данные на: https://my.telegram.org/auth")
    print("1. Авторизуйтесь в Telegram")
    print("2. Перейдите в 'API development tools'")
    print("3. Создайте приложение")
    print()
    
    while True:
        try:
            api_id = int(input("🔢 Введите API ID: "))
            break
        except ValueError:
            print("❌ API ID должен быть числом!")
    
    api_hash = input("🔑 Введите API Hash: ").strip()
    
    if not api_hash:
        print("❌ API Hash не может быть пустым!")
        sys.exit(1)
    
    return api_id, api_hash

async def generate_session(api_id, api_hash):
    print("\n🔄 Создание сессии...")
    
    client = TelegramClient('temp_session', api_id, api_hash)
    
    try:
        await client.start()
        session_string = client.session.save()
        
        print("\n🎉 SESSION_STRING УСПЕШНО СОЗДАН!")
        print("=" * 50)
        print(f"SESSION_STRING={session_string}")
        print("=" * 50)
        print("\n📋 ИНСТРУКЦИЯ:")
        print("1. Скопируйте строку выше")
        print("2. Откройте файл /home/scbot/sc-referral-bot/.env")
        print("3. Замените 'your_session_string_here' на полученную строку")
        print("4. Удалите этот скрипт: rm create_session.py temp_session.session")
        
    except Exception as e:
        print(f"❌ Ошибка создания сессии: {e}")
        sys.exit(1)
    
    finally:
        await client.disconnect()

def main():
    print_header()
    
    try:
        api_id, api_hash = get_api_credentials()
        asyncio.run(generate_session(api_id, api_hash))
    except KeyboardInterrupt:
        print("\n\n🛑 Операция отменена пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")

if __name__ == '__main__':
    main()
EOF

    sudo chmod +x $GENERATOR_FILE
    print_status "Генератор SESSION_STRING создан: $GENERATOR_FILE"
}

# Создание systemd сервиса
create_systemd_service() {
    print_info "Создание systemd сервиса..."
    
    SERVICE_FILE="/etc/systemd/system/scbot.service"
    
    sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=SC Referral Bot
After=network.target

[Service]
Type=simple
User=scbot
Group=scbot
WorkingDirectory=/home/scbot/sc-referral-bot
Environment=PATH=/home/scbot/sc-referral-bot/venv/bin
ExecStart=/home/scbot/sc-referral-bot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/scbot/sc-referral-bot

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable scbot
    
    print_status "Systemd сервис создан и активирован"
}

# Настройка Nginx
configure_nginx() {
    print_info "Настройка Nginx..."
    
    # Читаем домен из пользователя
    read -p "🌐 Введите ваш домен (например: bot.example.com): " DOMAIN
    
    if [ -z "$DOMAIN" ]; then
        DOMAIN="localhost"
        print_warning "Домен не указан, используется localhost"
    fi
    
    NGINX_CONFIG="/etc/nginx/sites-available/scbot"
    
    sudo tee $NGINX_CONFIG > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Основное приложение
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Статические файлы
    location /static/ {
        alias /home/scbot/sc-referral-bot/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Безопасность
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
}
EOF

    # Активируем конфигурацию
    sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Тестируем конфигурацию
    sudo nginx -t
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    print_status "Nginx настроен для домена: $DOMAIN"
}

# Создание скрипта управления
create_management_script() {
    print_info "Создание скрипта управления..."
    
    MGMT_SCRIPT="/home/scbot/sc-referral-bot/manage.sh"
    
    sudo -u scbot tee $MGMT_SCRIPT > /dev/null << 'EOF'
#!/bin/bash

# 🛠️ СКРИПТ УПРАВЛЕНИЯ SC REFERRAL BOT

case "$1" in
    start)
        echo "🚀 Запуск SC Referral Bot..."
        sudo systemctl start scbot
        sudo systemctl status scbot --no-pager
        ;;
    stop)
        echo "🛑 Остановка SC Referral Bot..."
        sudo systemctl stop scbot
        ;;
    restart)
        echo "🔄 Перезапуск SC Referral Bot..."
        sudo systemctl restart scbot
        sudo systemctl status scbot --no-pager
        ;;
    status)
        echo "📊 Статус SC Referral Bot:"
        sudo systemctl status scbot --no-pager
        ;;
    logs)
        echo "📋 Логи SC Referral Bot:"
        sudo journalctl -u scbot -f
        ;;
    update)
        echo "🔄 Обновление SC Referral Bot..."
        cd /home/scbot/sc-referral-bot
        git pull
        source venv/bin/activate
        pip install -r requirements.txt
        npm install
        sudo systemctl restart scbot
        echo "✅ Обновление завершено"
        ;;
    session)
        echo "🔐 Создание SESSION_STRING..."
        cd /home/scbot/sc-referral-bot
        source venv/bin/activate
        python create_session.py
        ;;
    *)
        echo "🛠️ УПРАВЛЕНИЕ SC REFERRAL BOT"
        echo "Использование: $0 {start|stop|restart|status|logs|update|session}"
        echo ""
        echo "Команды:"
        echo "  start    - Запустить бота"
        echo "  stop     - Остановить бота"  
        echo "  restart  - Перезапустить бота"
        echo "  status   - Показать статус"
        echo "  logs     - Показать логи (Ctrl+C для выхода)"
        echo "  update   - Обновить бота из GitHub"
        echo "  session  - Создать новый SESSION_STRING"
        exit 1
        ;;
esac
EOF

    sudo chmod +x $MGMT_SCRIPT
    
    # Создаем ссылку в /usr/local/bin для глобального доступа
    sudo ln -sf $MGMT_SCRIPT /usr/local/bin/scbot
    
    print_status "Скрипт управления создан: scbot {start|stop|restart|status|logs|update|session}"
}

# Настройка firewall
configure_firewall() {
    print_info "Настройка firewall..."
    
    # Проверяем наличие ufw
    if command -v ufw >/dev/null 2>&1; then
        sudo ufw allow ssh
        sudo ufw allow 80/tcp
        sudo ufw allow 443/tcp
        sudo ufw --force enable
        print_status "UFW firewall настроен"
    elif command -v firewall-cmd >/dev/null 2>&1; then
        sudo firewall-cmd --permanent --add-service=ssh
        sudo firewall-cmd --permanent --add-service=http
        sudo firewall-cmd --permanent --add-service=https
        sudo firewall-cmd --reload
        print_status "FirewallD настроен"
    else
        print_warning "Firewall не обнаружен, пропускаем настройку"
    fi
}

# Финальная настройка
final_setup() {
    print_info "Финальная настройка..."
    
    # Создаем директорию для логов
    sudo mkdir -p /var/log/scbot
    sudo chown scbot:scbot /var/log/scbot
    
    # Создаем директорию для статических файлов
    sudo -u scbot mkdir -p /home/scbot/sc-referral-bot/static
    
    # Настраиваем права доступа
    sudo chmod 755 /home/scbot/sc-referral-bot
    sudo chmod 644 /home/scbot/sc-referral-bot/.env
    
    print_status "Финальная настройка завершена"
}

# Вывод инструкций
print_instructions() {
    echo ""
    echo "🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!"
    echo "================================"
    echo ""
    echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
    echo ""
    echo "1️⃣ Отредактируйте конфигурацию:"
    echo "   sudo nano /home/scbot/sc-referral-bot/.env"
    echo ""
    echo "2️⃣ Создайте SESSION_STRING:"
    echo "   scbot session"
    echo ""
    echo "3️⃣ Запустите бота:"
    echo "   scbot start"
    echo ""
    echo "4️⃣ Проверьте статус:"
    echo "   scbot status"
    echo ""
    echo "📋 КОМАНДЫ УПРАВЛЕНИЯ:"
    echo "   scbot start    - Запустить"
    echo "   scbot stop     - Остановить"
    echo "   scbot restart  - Перезапустить"
    echo "   scbot status   - Статус"
    echo "   scbot logs     - Логи"
    echo "   scbot update   - Обновить"
    echo "   scbot session  - Создать SESSION_STRING"
    echo ""
    echo "🌐 ФАЙЛЫ КОНФИГУРАЦИИ:"
    echo "   Бот: /home/scbot/sc-referral-bot/.env"
    echo "   Nginx: /etc/nginx/sites-available/scbot"
    echo "   Systemd: /etc/systemd/system/scbot.service"
    echo ""
    echo "📊 МОНИТОРИНГ:"
    echo "   Логи бота: sudo journalctl -u scbot -f"
    echo "   Логи Nginx: sudo tail -f /var/log/nginx/access.log"
    echo ""
    print_status "Установка завершена! Отредактируйте .env файл и запустите бота."
}

# Главная функция
main() {
    echo "🚀 Начинаем автоматическую установку SC Referral Bot..."
    echo ""
    
    # Проверяем права root
    if [[ $EUID -eq 0 ]]; then
        print_error "Не запускайте скрипт от root! Используйте обычного пользователя с sudo."
        exit 1
    fi
    
    # Проверяем sudo доступ
    if ! sudo -n true 2>/dev/null; then
        print_error "Требуются sudo права для установки"
        exit 1
    fi
    
    detect_os
    
    # Установка зависимостей в зависимости от ОС
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        install_deps_debian
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"Rocky"* ]]; then
        install_deps_centos
    else
        print_warning "Неизвестная ОС: $OS. Пытаемся установить как Ubuntu/Debian..."
        install_deps_debian
    fi
    
    create_bot_user
    clone_repository
    install_python_deps
    install_node_deps
    create_env_file
    create_session_generator
    create_systemd_service
    configure_nginx
    create_management_script
    configure_firewall
    final_setup
    print_instructions
    
    echo ""
    print_status "🎉 АВТОМАТИЧЕСКАЯ УСТАНОВКА ЗАВЕРШЕНА!"
}

# Запуск основной функции
main "$@"