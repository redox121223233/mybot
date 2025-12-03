import asyncio
import json
import os
import sys
from urllib.parse import urlparse, parse_qsl

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
BOT_USERNAME = None

# Global instances for lazy initialization
bot_instance = None
dispatcher_instance = None
bot_initialized = False

async def initialize_bot():
    """
    Initializes the bot and dispatcher instances only once.
    """
    global Bot, Dispatcher, Update, DefaultBotProperties, ParseMode, router, BOT_TOKEN
    global bot_instance, dispatcher_instance, bot_initialized, BOT_USERNAME

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

    # Create and configure bot and dispatcher
    bot_instance = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher_instance = Dispatcher()
    dispatcher_instance.include_router(router)

    # Store bot username
    bot_info = await bot_instance.get_me()
    BOT_USERNAME = bot_info.username

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

def handler(request):
    """
    Vercel serverless function handler (compatible with Vercel's request object).
    """
    # This function must be synchronous.
    return asyncio.run(main_async(request))

async def main_async(request):
    """
    Asynchronous logic to handle different request types.
    """
    try:
        # Normalize Vercel's request object
        method = request.method
        parsed_url = urlparse(request.url)
        path = parsed_url.path
        query_params = dict(parse_qsl(parsed_url.query))

        # Route GET requests
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

            return create_response(200, {"message": "Hello from the bot's main page!"}) # Return a friendly message for the root path

        # Route POST requests
        if method == 'POST' and path == "/api/webhook":
            body = request.body
            try:
                update_data = json.loads(body)
                await handle_webhook(update_data)
                return create_response(200, {"status": "ok"})
            except json.JSONDecodeError:
                return create_response(400, {"error": "Invalid JSON"})

        return create_response(404, {"error": "Not Found"})

    except Exception as e:
        print(f"Error in handler: {e}")
        return create_response(500, {"error": "Internal Server Error", "details": str(e)})

def create_response(status_code, body_dict):
    """
    Helper to create a Vercel-compatible response dictionary.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body_dict),
    }
