import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
import nest_asyncio

# Apply nest_asyncio
nest_asyncio.apply()

# Ensure the project root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Global variables for caching
BOT_INSTANCE = None
DISPATCHER_INSTANCE = None
LOOP = None

def get_bot_and_dispatcher():
    """Lazy initialization of Bot and Dispatcher to avoid issubclass errors during module load."""
    global BOT_INSTANCE, DISPATCHER_INSTANCE
    if BOT_INSTANCE is None:
        from aiogram import Bot, Dispatcher
        from bot_core.config import BOT_TOKEN
        from bot_core.handlers import router

        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN is not configured.")

        BOT_INSTANCE = Bot(token=BOT_TOKEN)
        DISPATCHER_INSTANCE = Dispatcher()
        DISPATCHER_INSTANCE.include_router(router)
    return BOT_INSTANCE, DISPATCHER_INSTANCE

def get_loop():
    global LOOP
    if LOOP is None:
        try:
            LOOP = asyncio.get_running_loop()
        except RuntimeError:
            LOOP = asyncio.new_event_loop()
            asyncio.set_event_loop(LOOP)
    return LOOP

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handles incoming POST requests from Telegram."""
        loop = get_loop()

        async def process_update():
            try:
                bot, dp = get_bot_and_dispatcher()

                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                update_data = json.loads(body.decode('utf-8'))

                from aiogram.types import Update
                update = Update.model_validate(update_data, context={"bot": bot})

                await dp.feed_update(bot=bot, update=update)

                self.send_response(200)
                self.end_headers()

            except Exception as e:
                print(f"Error processing update: {e}")
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()

        loop.run_until_complete(process_update())

    def do_GET(self):
        """Health check."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
