"""Vercel serverless function for Telegram webhook - Optimized"""
import os
import sys
import json
from http.server import BaseHTTPRequestHandler
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=2)

def process_update_sync(update_data):
    """Process update in background thread"""
    try:
        from bot import process_update
        asyncio.run(process_update(update_data))
    except Exception as e:
        print(f"Background processing error: {e}")
        import traceback
        traceback.print_exc()

class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler - Fast response"""

    def do_GET(self):
        """Handle GET requests (health check)"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok'}).encode())

    def do_POST(self):
        """Handle POST requests (webhook) - Immediate response"""
        try:
            # Read and parse request
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            update_data = json.loads(body.decode('utf-8'))

            # Send immediate response to Telegram
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'ok': True,
                'update_id': update_data.get('update_id')
            }).encode())

            # Process in background (don't wait)
            executor.submit(process_update_sync, update_data)

        except Exception as e:
            print(f"Webhook error: {e}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
