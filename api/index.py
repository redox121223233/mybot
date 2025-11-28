from flask import Flask, request
from telegram import Update
import asyncio
import nest_asyncio

from bot import build_application

# This file is the entry point for Vercel.

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

app = Flask(__name__)
application = build_application()

async def main(data):
    """Initializes the bot (if needed) and processes one update."""
    if not hasattr(main, 'initialized'):
        await application.initialize()
        main.initialized = True

    await application.process_update(Update.de_json(data, application.bot))

@app.route('/api/index', methods=['POST'])
def webhook():
    """Webhook endpoint to receive updates from Telegram."""
    loop = asyncio.get_event_loop()
    data = request.get_json(force=True)
    loop.run_until_complete(main(data))
    return 'ok'

@app.route('/')
def index():
    """A simple endpoint to confirm the server is running."""
    return 'Hello, World!'
