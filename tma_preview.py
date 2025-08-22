#!/usr/bin/env python3
"""
Простой HTTP сервер для превью TMA с моковыми данными
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import json
from urllib.parse import urlparse, parse_qs
import sys

class TMAPreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='tma', **kwargs)
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        # API endpoints для превью
        if parsed.path == '/api/tma/products':
            self.send_api_response([
                {
                    "id": "stars_50",
                    "title": "50 ⭐ Stars",
                    "description": "Идеально для начала",
                    "price": 50,
                    "benefits": [
                        "Доступ к премиум стикерам",
                        "Увеличение лимитов чатов",
                        "Приоритетная поддержка"
                    ],
                    "popular": False
                },
                {
                    "id": "stars_100", 
                    "title": "100 ⭐ Stars",
                    "description": "Популярный выбор",
                    "price": 100,
                    "benefits": [
                        "Все возможности 50 Stars",
                        "Расширенные настройки профиля",
                        "Эксклюзивные темы"
                    ],
                    "popular": True
                },
                {
                    "id": "stars_250",
                    "title": "250 ⭐ Stars", 
                    "description": "Максимум возможностей",
                    "price": 250,
                    "benefits": [
                        "Все возможности 100 Stars",
                        "VIP статус в каналах",
                        "Персональные рекомендации"
                    ],
                    "popular": False
                },
                {
                    "id": "stars_500",
                    "title": "500 ⭐ Stars",
                    "description": "Премиум пакет",
                    "price": 500,
                    "benefits": [
                        "Все возможности 250 Stars",
                        "Эксклюзивный контент",
                        "Персональный менеджер"
                    ],
                    "popular": False
                }
            ])
            return
            
        elif parsed.path.startswith('/api/tma/user/') and parsed.path.endswith('/balance'):
            self.send_api_response({"balance": 42.5})
            return
            
        # Обычные файлы
        super().do_GET()
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/api/tma/create-invoice':
            # Мок ответ для создания инвойса
            self.send_api_response({
                "success": True,
                "stars_quantity": 50,
                "product": "Stars Package",
                "instructions": {
                    "address": "UQD2NmD_lH5f_VN2_6h...",
                    "amount": 1000000000,
                    "payload": "invoice_12345"
                }
            })
            return
            
        self.send_error(404)
    
    def send_api_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    server = HTTPServer(('0.0.0.0', port), TMAPreviewHandler)
    print(f"TMA Preview Server running on port {port}")
    print(f"Open http://localhost:{port} to view")
    server.serve_forever()