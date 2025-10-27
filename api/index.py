from flask import Flask, request, jsonify
import logging
import os
import sys
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
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

CHANNEL_USERNAME = "@redoxbot_sticker"
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919
DAILY_LIMIT = 5
BOT_USERNAME = ""

# Initialize Telegram Application
application = Application.builder().token(BOT_TOKEN).build()

# Import handlers after setting up application
try:
    # Add the parent directory to the path so we can import handlers
    sys.path.append('/var/task')
    from handlers import *
    
    # Setup handlers
    setup_handlers(application)
    logger.info("Handlers setup completed successfully")
except ImportError as e:
    logger.error(f"Error importing handlers: {e}")
except Exception as e:
    logger.error(f"Error setting up handlers: {e}")

# Add a default message handler to catch all updates
async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Received message: {update.message.text if update.message else 'No message text'}")
    if update.message and update.message.text:
        await update.message.reply_text(
            "🤖 ربات شما دریافت شد! برای دیدن دستورات، /help را وارد کنید.\n\n"
            "دستورات موجود:\n"
            "/start - شروع ربات\n"
            "/help - راهنما\n"
            "/search <متن> - جستجو\n"
            "/music <آهنگ> - موسیقی\n"
            "/weather <شهر> - آب و هوا\n"
            "و بسیاری دیگر..."
        )

# Add the handler as the last one (lowest priority)
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_all_messages))

@app.route('/')
def home():
    return "Telegram Bot is running! All handlers are active."

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        try:
            update_data = request.get_json()
            logger.info(f"Received webhook data: {update_data}")
            
            update = Update.de_json(update_data, application.bot)
            application.process_update(update)
            
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error"}), 400

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "handlers": "active"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
