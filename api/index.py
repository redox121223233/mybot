import asyncio
import json
import os
import sys
from urllib.parse import urlparse
import nest_asyncio

# Apply nest_asyncio to allow running asyncio event loops within other event loops.
nest_asyncio.apply()

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

    from aiogram import Bot as AiogramBot, Dispatcher as AiogramDispatcher
    from aiogram.client.default import DefaultBotProperties as AiogramDefaultBotProperties
    from aiogram.enums import ParseMode as AiogramParseMode
    from aiogram.types import Update as AiogramUpdate

    from bot_core.bot_logic import router as bot_router
    from bot_core.config import BOT_TOKEN as token
    import bot_core.handlers
    import bot_core.start_handler

    Bot, Dispatcher, Update, DefaultBotProperties, ParseMode = AiogramBot, AiogramDispatcher, AiogramUpdate, AiogramDefaultBotProperties, AiogramParseMode
    router, BOT_TOKEN = bot_router, token

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")

    # Disable default timeout as a workaround for the "Timeout context manager" error in serverless env
    bot_properties = DefaultBotProperties(parse_mode=ParseMode.HTML, request_timeout=None)
    bot_instance = Bot(token=BOT_TOKEN, default=bot_properties)

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

    webhook_url = f"https://{url}/webhook"
    await bot_instance.set_webhook(webhook_url)
    return f"Webhook set to {webhook_url}"

def create_response(status_code, body_dict):
    """
    Helper to create a Vercel-compatible response dictionary.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict),
    }

async def main_async(request):
    """
    Asynchronous logic to handle different request types.
    """
    try:
        method = request.method
        path = urlparse(request.url).path

        if method == 'GET':
            if path == "/api/health":
                return create_response(200, {"status": "healthy", "bot_initialized": bot_initialized})
            if path == "/api/set_webhook":
                vercel_url = request.headers.get('x-vercel-deployment-url')
                if vercel_url:
                    message = await set_telegram_webhook(vercel_url)
                    return create_response(200, {"status": "ok", "message": message})
                else:
                    return create_response(400, {"status": "error", "message": "x-vercel-deployment-url header not found"})
            return create_response(200, {"message": "Hello from the bot's main page!"})

        if method == 'POST' and path == "/webhook":
            body = request.body
            update_data = json.loads(body)
            await handle_webhook(update_data)
            return create_response(200, {"status": "ok"})

        return create_response(404, {"error": "Not Found"})

    except Exception as e:
        print(f"Error processing update: {e}")
        return create_response(500, {"error": "Internal Server Error", "details": str(e)})

def handler(request):
    """
    Vercel serverless function handler.
    """
    return asyncio.run(main_async(request))
