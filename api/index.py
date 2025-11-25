from flask import Flask, request as flask_request
from telegram import Update
import asyncio
import os

from bot import build_application

# This file is the entry point for Vercel.
# It imports the bot application and handles webhook requests.

app = Flask(__name__)
application = build_application()

async def post_init():
    if 'VERCEL_URL' in os.environ:
        webhook_url = f"https://{os.environ['VERCEL_URL']}/api/index"
        await application.bot.set_webhook(url=webhook_url)

async def main():
    if not hasattr(main, 'initialized'):
        await application.initialize()
        await post_init()
        main.initialized = True

    update = Update.de_json(flask_request.get_json(force=True), application.bot)
    await application.process_update(update)

@app.route('/api/index', methods=['POST'])
def webhook():
    asyncio.run(main())
    return 'ok'

@app.route('/')
def index():
    return 'Hello, World!'
