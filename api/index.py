
import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
import traceback

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Initialize Bot and Dispatcher ---
bot = None
dp = None
BOT_INITIALIZED = False
try:
    from aiogram import Bot, Dispatcher
    from aiogram.types import Update
    from bot_core.config import BOT_TOKEN
    from bot_core.handlers import router

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set.")
        
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    print("--- BOT INITIALIZED SUCCESSFULLY ---")
    BOT_INITIALIZED = True
except Exception as e:
    print("--- FAILED TO INITIALIZE BOT ---")
    print(f"Error: {e}")
    traceback.print_exc()

# --- Event Loop Management ---
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not BOT_INITIALIZED:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Bot is not initialized.'}).encode())
            return

        async def process_update():
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                update_data = json.loads(post_data.decode('utf-8'))

                update = Update.model_validate(update_data, context={"bot": bot})
                await dp.feed_update(bot=bot, update=update)

                self.send_response(200)
                self.end_headers()
            except Exception as e:
                print(f"--- ERROR PROCESSING UPDATE ---")
                print(f"Error: {e}")
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()

        loop.run_until_complete(process_update())

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            'status': 'ok',
            'bot_initialized': BOT_INITIALIZED
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
