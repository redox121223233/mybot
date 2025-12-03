import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

# Add parent directory to path to allow imports from bot_core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy-loaded imports
Bot = None
Dispatcher = None
Update = None
DefaultBotProperties = None
ParseMode = None
router = None
BOT_TOKEN = None

# Global instances for lazy initialization
bot_instance = None
dispatcher_instance = None
bot_initialized = False

async def initialize_bot():
    """
    Initializes the bot and dispatcher instances only once.
    """
    global Bot, Dispatcher, Update, DefaultBotProperties, ParseMode, router, BOT_TOKEN
    global bot_instance, dispatcher_instance, bot_initialized

    if bot_initialized:
        return

    # Dynamically import heavy libraries
    from aiogram import Bot as AiogramBot, Dispatcher as AiogramDispatcher
    from aiogram.client.default import DefaultBotProperties as AiogramDefaultBotProperties
    from aiogram.enums import ParseMode as AiogramParseMode
    from aiogram.types import Update as AiogramUpdate

    # Import bot-specific modules
    from bot_core.bot_logic import router as bot_router
    from bot_core.config import BOT_TOKEN as token

    # Assign to global scope for reuse
    Bot, Dispatcher, Update, DefaultBotProperties, ParseMode = AiogramBot, AiogramDispatcher, AiogramUpdate, AiogramDefaultBotProperties, AiogramParseMode
    router, BOT_TOKEN = bot_router, token

    # Validate bot token
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")

    # Create and configure bot and dispatcher
    bot_instance = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher_instance = Dispatcher()
    dispatcher_instance.include_router(router)

    bot_initialized = True
    print("Bot initialized successfully!")

async def handle_webhook(update_data):
    """
    Handles a webhook update from Telegram.
    """
    if not bot_initialized:
        await initialize_bot()

    update = Update.model_validate(update_data, context={"bot": bot_instance})
    await dispatcher_instance.feed_update(bot=bot_instance, update=update)

async def set_telegram_webhook(url):
    """
    Sets the Telegram webhook to the provided URL.
    """
    if not bot_initialized:
        await initialize_bot()

    webhook_url = f"https://{url}/api/webhook"
    await bot_instance.set_webhook(webhook_url)
    return f"Webhook set to {webhook_url}"

class handler(BaseHTTPRequestHandler):
    """
    Vercel serverless function handler.
    """
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/api/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"status": "healthy", "bot_initialized": bot_initialized}
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif path == "/api/set_webhook":
            vercel_url = self.headers.get('x-vercel-deployment-url')
            if vercel_url:
                try:
                    message = asyncio.run(set_telegram_webhook(vercel_url))
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    response = {"status": "ok", "message": message}
                    self.wfile.write(json.dumps(response).encode("utf-8"))
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    response = {"status": "error", "message": str(e)}
                    self.wfile.write(json.dumps(response).encode("utf-8"))
            else:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"status": "error", "message": "x-vercel-deployment-url header not found"}
                self.wfile.write(json.dumps(response).encode("utf-8"))
        
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Hello from the bot's main page!")

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/api/webhook":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)

            try:
                update_data = json.loads(post_body.decode("utf-8"))
                asyncio.run(handle_webhook(update_data))
                self.send_response(200)
            except Exception as e:
                print(f"Error processing update: {e}")
                self.send_response(500)

            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()
