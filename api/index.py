from flask import Flask, request as flask_request
from telegram import Update
import asyncio
import os
import nest_asyncio

from bot import build_application

# Apply nest_asyncio to allow nested event loops, crucial for Vercel + Flask + PTB
nest_asyncio.apply()

app = Flask(__name__)
application = build_application()

async def initialize_bot():
    """Initializes the bot and sets the webhook, runs only once."""
    if not hasattr(initialize_bot, 'initialized'):
        await application.initialize()
        if 'VERCEL_URL' in os.environ:
            webhook_url = f"https://{os.environ['VERCEL_URL']}/api/index"
            await application.bot.set_webhook(url=webhook_url)
        initialize_bot.initialized = True

async def process_update(data):
    """Processes a single update."""
    await application.process_update(Update.de_json(data, application.bot))

@app.route('/api/index', methods=['POST'])
def webhook():
    """Webhook endpoint to receive updates from Telegram."""
    # Initialize bot on the first request
    asyncio.run(initialize_bot())

    # Process the update
    data = flask_request.get_json(force=True)
    asyncio.run(process_update(data))

    return 'ok'

@app.route('/')
def index():
    """A simple endpoint to confirm the server is running."""
    return 'Hello, World!'
