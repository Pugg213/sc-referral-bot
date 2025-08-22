#!/usr/bin/env python3
"""
📦 Создание пакета для деплоя на сторонний сервер
"""
import os
import shutil
import tarfile
from datetime import datetime

def create_deployment_package():
    """Создает готовый архив для деплоя на сервер"""
    
    # Файлы и директории для включения в пакет
    include_files = [
        # Основные файлы Python
        'main.py', 'run.py', 'start_server.py',
        'simple_session_generator.py', 'generate_session.py',
        
        # Конфигурационные файлы
        'pyproject.toml', 'server_requirements.txt',
        'env_example.txt', 'Dockerfile',
        'deploy_instructions.md',
        
        # База данных (если есть)
        'bot.db',
        
        # Директории с кодом
        'app/', 'src/', 'public/', 'assets/', 'tma/',
        
        # Frontend файлы
        'package.json', 'vite.config.js', 'index.html',
        
        # Статические файлы
        'tonconnect-manifest.json', 'privacy.html', 'terms.html',
        'icon.svg', 'icon-192.png', 'icon-192.svg'
    ]
    
    # Создать временную директорию
    package_name = f"sc-bot-deploy-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    temp_dir = f"/tmp/{package_name}"
    
    print(f"📦 Создаю пакет для деплоя: {package_name}")
    
    # Создать директорию
    os.makedirs(temp_dir, exist_ok=True)
    
    copied_files = []
    
    # Копировать файлы
    for item in include_files:
        src_path = item
        dst_path = os.path.join(temp_dir, item)
        
        try:
            if os.path.isfile(src_path):
                # Копировать файл
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                copied_files.append(f"✅ {src_path}")
                
            elif os.path.isdir(src_path):
                # Копировать директорию
                shutil.copytree(src_path, dst_path, ignore=shutil.ignore_patterns(
                    '*.pyc', '__pycache__', '*.log', '*.session', 'node_modules'
                ))
                copied_files.append(f"📁 {src_path}/")
                
            else:
                copied_files.append(f"⚠️ {src_path} (не найден)")
                
        except Exception as e:
            copied_files.append(f"❌ {src_path} (ошибка: {e})")
    
    # Создать архив
    archive_name = f"{package_name}.tar.gz"
    archive_path = os.path.join(os.getcwd(), archive_name)
    
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(temp_dir, arcname=package_name)
    
    # Удалить временную директорию
    shutil.rmtree(temp_dir)
    
    # Показать результат
    print("\\n" + "="*60)
    print("📋 ФАЙЛЫ В ПАКЕТЕ:")
    for file_info in copied_files:
        print(f"   {file_info}")
    
    print("\\n" + "="*60)
    print(f"✅ ПАКЕТ СОЗДАН: {archive_name}")
    print(f"📏 Размер: {os.path.getsize(archive_path) / 1024 / 1024:.1f} MB")
    print("\\n🚀 ГОТОВ К ДЕПЛОЮ НА СТОРОННИЙ СЕРВЕР!")
    print("\\n📋 СЛЕДУЮЩИЕ ШАГИ:")
    print("1. Скачать архив на свой компьютер")
    print("2. Загрузить на сервер (scp, ftp, etc)")
    print("3. Распаковать: tar -xzf " + archive_name)
    print("4. Следовать инструкциям в deploy_instructions.md")
    
    return archive_path

if __name__ == "__main__":
    try:
        archive_path = create_deployment_package()
        print(f"\\n📦 Архив готов: {archive_path}")
    except Exception as e:
        print(f"❌ Ошибка создания пакета: {e}")
        import traceback
        traceback.print_exc()