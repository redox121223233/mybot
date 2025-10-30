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
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables")
    # Don't exit here, let Vercel handle it
    # sys.exit(1)

try:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Import handlers after setting up application
    # Add the parent directory to the path so we can import handlers
    sys.path.append('/var/task')
    
    # Try to import handlers but don't fail if they don't exist
    try:
        from handlers import *
        # Setup handlers
        setup_handlers(application)
        logger.info("Handlers setup completed successfully")
    except ImportError as e:
        logger.warning(f"Handlers not available: {e}")
        # Add a simple start handler
        async def start_command(update, context):
            await update.message.reply_text("🤖 ربات شما فعال است!")
        
        async def help_command(update, context):
            await update.message.reply_text("/start - شروع\n/help - راهنما")
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        logger.info("Basic handlers setup completed")
    
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

except Exception as e:
    logger.error(f"Error setting up Telegram application: {e}")
    application = None

@app.route('/')
def home():
    return "Telegram Bot is running! All handlers are active."

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        try:
            update_data = request.get_json()
            logger.info(f"Received webhook data: {update_data}")
            
            if application:
                update = Update.de_json(update_data, application.bot)
                application.process_update(update)
            else:
                logger.warning("Telegram application not initialized")
            
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error"}), 400

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "handlers": "active", "telegram_app": application is not None})

# Vercel serverless handler
def handler(request):
    """
    Vercel serverless function handler
    """
    return app

# Export for Vercel
app = app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))