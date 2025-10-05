"""Vercel serverless function for Telegram webhook - Optimized"""
import os
import sys
import json
import traceback
from http.server import BaseHTTPRequestHandler

from async_loop import submit

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def submit_update(update_data):
    """Schedule update processing on persistent event loop"""
    from bot import process_update
    submit(process_update(update_data))

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

            # Process asynchronously without blocking response
            submit_update(update_data)

        except Exception as e:
            print(f"Webhook error: {e}")
            traceback.print_exc()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
