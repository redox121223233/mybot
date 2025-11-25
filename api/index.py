from flask import Flask, request as flask_request
from telegram import Update
import asyncio
import os

from bot import build_application

# This file is the entry point for Vercel.

app = Flask(__name__)
application = build_application()

async def main(data):
    """Processes the incoming update."""
    if not hasattr(main, 'initialized'):
        # Initialize the bot once, on the first request
        await application.initialize()
        main.initialized = True

    update = Update.de_json(data, application.bot)
    await application.process_update(update)

@app.route('/api/index', methods=['POST'])
def webhook():
    """Webhook endpoint to receive updates from Telegram."""
    data = flask_request.get_json(force=True)
    asyncio.run(main(data))
    return 'ok'

@app.route('/')
def index():
    """A simple endpoint to confirm the server is running."""
    return 'Hello, World!'
