"""Vercel serverless function for Telegram webhook - Fixed event loop"""
import os
import sys
import json
from http.server import BaseHTTPRequestHandler
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Global event loop
_loop = None

def get_event_loop():
    """Get or create event loop"""
    global _loop
    try:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_loop)
        return _loop
    except Exception as e:
        print(f"Error getting event loop: {e}")
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        return _loop

def process_update_sync(update_data):
    """Process update synchronously"""
    try:
        from bot import process_update

        # Get or create event loop
        loop = get_event_loop()

        # Run update processing
        loop.run_until_complete(process_update(update_data))

    except Exception as e:
        print(f"Error processing update: {e}")
        import traceback
        traceback.print_exc()

class handler(BaseHTTPRequestHandler):
    """Vercel serverless handler"""

    def do_GET(self):
        """Handle GET requests (health check)"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok'}).encode())

    def do_POST(self):
        """Handle POST requests (webhook)"""
        try:
            # Read and parse request
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            update_data = json.loads(body.decode('utf-8'))

            # Process update immediately (blocking)
            process_update_sync(update_data)

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'ok': True,
                'update_id': update_data.get('update_id')
            }).encode())

        except Exception as e:
            print(f"Webhook error: {e}")
            import traceback
            traceback.print_exc()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
