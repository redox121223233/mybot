import asyncio
import json
import os
import sys
import traceback
import logging
from http.server import BaseHTTPRequestHandler
import nest_asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
            logger.error("BOT_TOKEN is not configured in environment variables.")
            raise ValueError("BOT_TOKEN is not configured.")

        logger.info("Initializing Bot and Dispatcher...")
        BOT_INSTANCE = Bot(token=BOT_TOKEN)
        DISPATCHER_INSTANCE = Dispatcher()
        DISPATCHER_INSTANCE.include_router(router)
        logger.info("Bot and Dispatcher initialized successfully.")
    return BOT_INSTANCE, DISPATCHER_INSTANCE

def get_loop():
    global LOOP
    if LOOP is None:
        try:
            LOOP = asyncio.get_running_loop()
            logger.info("Using existing asyncio loop.")
        except RuntimeError:
            LOOP = asyncio.new_event_loop()
            asyncio.set_event_loop(LOOP)
            logger.info("Created new asyncio loop.")
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

                logger.info(f"Received update: {update_data.get('update_id')}")

                from aiogram.types import Update
                update = Update.model_validate(update_data, context={"bot": bot})

                # Feed the update to the dispatcher
                await dp.feed_update(bot=bot, update=update)
                logger.info(f"Successfully processed update: {update.update_id}")

                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))

            except Exception as e:
                logger.error(f"Error processing update: {e}")
                logger.error(traceback.format_exc())
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

        loop.run_until_complete(process_update())

    def do_GET(self):
        """Health check."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        bot_initialized = BOT_INSTANCE is not None
        self.wfile.write(json.dumps({'status': 'ok', 'bot_initialized': bot_initialized}).encode('utf-8'))
