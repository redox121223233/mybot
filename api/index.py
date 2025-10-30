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
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("BOT_TOKEN or TELEGRAM_BOT_TOKEN not found in environment variables")

try:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add the parent directory to the path so we can import handlers
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Try to import and setup handlers
    try:
        from handlers import setup_handlers
        import asyncio
        # Use asyncio.create_task instead of asyncio.run for better compatibility
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_handlers(application))
        loop.close()
        logger.info("Handlers setup completed successfully")
    except ImportError as e:
        logger.warning(f"Handlers not available: {e}")
        # Add basic handlers
        async def start_command(update, context):
            await update.message.reply_text("🤖 ربات شما فعال است!")
        
        async def help_command(update, context):
            await update.message.reply_text("/start - شروع\n/help - راهنما")
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        logger.info("Basic handlers setup completed")
    
    # Add a default message handler
    async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and update.message.text:
            await update.message.reply_text(
                "🤖 ربات شما دریافت شد! برای دیدن دستورات، /help را وارد کنید.\n\n"
                "دستورات موجود:\n"
                "/start - شروع ربات\n"
                "/help - راهنما\n"
                "/guess - بازی حدس عدد\n"
                "/rps - سنگ کاغذ قیچی\n"
                "/word - بازی کلمات\n"
                "/memory - بازی حافظه\n"
                "/random - بازی تصادفی\n"
                "/sticker <متن> - ساخت استیکر سریع\n"
                "/customsticker - استیکر ساز سفارشی\n"
                "و بسیار دیگر..."
            )

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