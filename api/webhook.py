"""Vercel serverless function for Telegram webhook - Optimized"""
import os
import sys
import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Persistent event loop running in dedicated thread
_event_loop = asyncio.new_event_loop()

def _loop_runner(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

_thread = threading.Thread(target=_loop_runner, args=(_event_loop,), daemon=True)
_thread.start()

def _handle_future_result(future):
    try:
        future.result()
    except Exception as exc:
        print(f"Background processing error: {exc}")
        traceback.print_exc()

def submit_update(update_data):
    """Schedule update processing on persistent event loop"""
    from bot import process_update
    future = asyncio.run_coroutine_threadsafe(process_update(update_data), _event_loop)
    future.add_done_callback(_handle_future_result)

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
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
