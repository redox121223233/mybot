from flask import Flask, request, jsonify
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Telegram bot
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Import and setup handlers
from handlers import setup_handlers
import asyncio
asyncio.run(setup_handlers(application))

@app.route('/')
def home():
    return "Telegram Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(), application.bot)
        application.process_update(update)
        return jsonify({"status": "ok"}), 200
    return jsonify({"status": "error"}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))