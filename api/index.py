import asyncio
import json
import os
import sys
import traceback
import logging
from http.server import BaseHTTPRequestHandler
import nest_asyncio

# Configure logging to stdout immediately
root = logging.getLogger()
root.setLevel(logging.INFO)
handler_log = logging.StreamHandler(sys.stdout)
handler_log.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root.addHandler(handler_log)

logger = logging.getLogger(__name__)

# Apply nest_asyncio
nest_asyncio.apply()

# Ensure the project root is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Global variables for caching
BOT_INSTANCE = None
DISPATCHER_INSTANCE = None
LOOP = None
BOT_LOOP = None

def get_bot_and_dispatcher(loop):
    """Lazy initialization of Bot and Dispatcher."""
    global BOT_INSTANCE, DISPATCHER_INSTANCE, BOT_LOOP
    if BOT_INSTANCE is not None and BOT_LOOP is not loop:
        logger.info("Event loop changed! Recreating Bot instance to match current loop.")
        try:
            loop.create_task(BOT_INSTANCE.session.close())
        except Exception as e:
            logger.warning(f"Failed to close old bot session: {e}")
        BOT_INSTANCE = None

    if BOT_INSTANCE is None:
        from aiogram import Bot, Dispatcher
        from bot_core.config import BOT_TOKEN
        from bot_core.handlers import router

        if not BOT_TOKEN:
            logger.error("BOT_TOKEN is not configured.")
            raise ValueError("BOT_TOKEN is not configured.")

        logger.info("Initializing Bot and Dispatcher...")
        BOT_INSTANCE = Bot(token=BOT_TOKEN)
        DISPATCHER_INSTANCE = Dispatcher()
        DISPATCHER_INSTANCE.include_router(router)
        BOT_LOOP = loop
        logger.info("Bot and Dispatcher initialized successfully.")
    return BOT_INSTANCE, DISPATCHER_INSTANCE

def get_loop():
    global LOOP
    if LOOP is not None and LOOP.is_closed():
        logger.info("Cached event loop was closed. Resetting LOOP to None.")
        LOOP = None
    if LOOP is None:
        try:
            LOOP = asyncio.get_running_loop()
            logger.info("Attached to existing loop.")
        except RuntimeError:
            LOOP = asyncio.new_event_loop()
            asyncio.set_event_loop(LOOP)
            logger.info("Created new loop.")
    return LOOP

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handles incoming POST requests from Telegram."""
        loop = get_loop()

        async def process_update():
            try:
                bot, dp = get_bot_and_dispatcher(loop)

                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                body_decoded = body.decode('utf-8')
                update_data = json.loads(body_decoded)

                logger.info(f"Update received: {update_data.get('update_id')} - Data: {body_decoded}")

                from aiogram.types import Update
                update = Update.model_validate(update_data, context={"bot": bot})

                await dp.feed_update(bot=bot, update=update)
                logger.info(f"Update {update.update_id} processed.")

                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))

            except Exception as e:
                logger.error(f"Error: {e}")
                logger.error(traceback.format_exc())
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

        loop.run_until_complete(process_update())

    def do_GET(self):
        """Health and Diagnostic check."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # Diagnostics
        from bot_core.utils.video_processing import get_ffmpeg_path
        loop = get_loop()
        ffmpeg_path = loop.run_until_complete(get_ffmpeg_path())

        # Test bot initialization
        bot_init_success = False
        bot_init_error = None
        try:
            bot, dp = get_bot_and_dispatcher(loop)
            bot_init_success = True
        except Exception as e:
            bot_init_error = str(e)

        from bot_core.config import BOT_TOKEN
        token_found = BOT_TOKEN is not None
        token_length = len(BOT_TOKEN) if BOT_TOKEN else 0
        token_preview = f"{BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}" if BOT_TOKEN and len(BOT_TOKEN) > 20 else "not_configured"

        diag = {
            'status': 'ok',
            'bot_initialized_cache': BOT_INSTANCE is not None,
            'bot_init_test_success': bot_init_success,
            'bot_init_test_error': bot_init_error,
            'token_configured': token_found,
            'token_length_chars': token_length,
            'token_preview_safe': token_preview,
            'ffmpeg_path': ffmpeg_path,
            'ffmpeg_exists': os.path.exists(ffmpeg_path) if ffmpeg_path else False,
            'cwd': os.getcwd(),
            'ls_bin': os.listdir('bin') if os.path.exists('bin') else 'bin_not_found',
            'env': {k: v for k, v in os.environ.items() if 'TOKEN' not in k and 'ID' not in k}
        }
        self.wfile.write(json.dumps(diag).encode('utf-8'))
