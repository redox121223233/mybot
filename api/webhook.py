"""Vercel serverless function for Telegram webhook"""
import os
import sys
import json
from http.server import BaseHTTPRequestHandler
import asyncio
import threading

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Thread-safe event loop management
_loop = None
_loop_lock = threading.Lock()

def get_or_create_event_loop():
    """Get or create a new event loop safely"""
    global _loop

    with _loop_lock:
        # Always create a fresh loop to avoid closed loop issues
        try:
            # Close old loop if exists
            if _loop is not None and not _loop.is_closed():
                try:
                    _loop.close()
                except:
                    pass
        except:
            pass

        # Create new loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        return _loop

def run_async_in_new_thread(coro):
    """Run async coroutine in a new thread with its own event loop"""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro)
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join(timeout=50)  # 50 second timeout

def process_update_blocking(update_data):
    """Process update in a blocking manner with new event loop"""
    try:
        from bot import process_update

        # Create completely fresh event loop for each request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Run the update processing
            loop.run_until_complete(process_update(update_data))
        finally:
            # Keep loop open for pending tasks
            try:
                # Give pending tasks a chance to complete
                pending = asyncio.all_tasks(loop)
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except:
                pass

            # Now close the loop
            try:
                loop.close()
            except:
                pass

    except Exception as e:
        print(f"❌ Error processing update: {e}")
        import traceback
        traceback.print_exc()

class handler(BaseHTTPRequestHandler):
    """Vercel webhook handler"""

    def do_GET(self):
        """Health check"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'version': '2.0'}).encode())

    def do_POST(self):
        """Process webhook"""
        try:
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            update_data = json.loads(body.decode('utf-8'))

            update_id = update_data.get('update_id')
            update_type = 'message' if 'message' in update_data else 'callback_query' if 'callback_query' in update_data else 'other'

            print(f"📨 Update {update_id} - Type: {update_type}")

            if update_type == 'callback_query':
                cb_data = update_data.get('callback_query', {}).get('data', 'N/A')
                print(f"🔘 Callback data: {cb_data}")

            # Process update (blocking)
            process_update_blocking(update_data)

            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'ok': True,
                'update_id': update_data.get('update_id')
            }).encode())

        except Exception as e:
            print(f"❌ Webhook error: {e}")
            import traceback
            traceback.print_exc()

            # Always return 200 to prevent Telegram retries
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
