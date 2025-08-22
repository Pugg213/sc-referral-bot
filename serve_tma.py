"""
Simple static file server for TMA production build
Serves dist/ folder on port 80 for Telegram Mini App
"""
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import logging

class TMATHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="dist", **kwargs)
    
    def end_headers(self):
        # Add headers required for TMA
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def run_tma_server():
    """Run TMA server on port 80"""
    port = 80
    
    try:
        server = HTTPServer(('0.0.0.0', port), TMATHandler)
        logging.info(f"🌐 TMA Server running on port {port}")
        logging.info(f"📱 TMA URL: http://localhost:{port}")
        server.serve_forever()
    except PermissionError:
        # Fallback to port 8080 if 80 is restricted
        port = 8080
        server = HTTPServer(('0.0.0.0', port), TMATHandler)
        logging.info(f"🌐 TMA Server running on port {port} (fallback)")
        logging.info(f"📱 TMA URL: http://localhost:{port}")
        server.serve_forever()
    except Exception as e:
        logging.error(f"TMA Server failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Check if dist exists
    if not os.path.exists("dist"):
        logging.error("❌ dist/ folder not found. Run 'npm run build' first.")
        exit(1)
    
    run_tma_server()