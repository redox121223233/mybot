import os
import sys

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def lambda_handler(event, context):
    """
    AWS Lambda style handler - more compatible with Vercel
    """
    try:
        # Import dependencies only when needed
        from flask import Flask, request, jsonify
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
        
        app = Flask(__name__)
        
        # Get token
        TELEGRAM_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        
        if not TELEGRAM_TOKEN:
            logger.error("No token found")
            return {
                'statusCode': 500,
                'body': 'No token configured'
            }
        
        # Initialize application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Basic handlers
        async def start_command(update, context):
            await update.message.reply_text("🤖 ربات شما فعال است!")
        
        async def help_command(update, context):
            await update.message.reply_text("/start - شروع\n/help - راهنما")
        
        async def handle_message(update, context):
            if update.message and update.message.text:
                await update.message.reply_text("🤖 ربات شما دریافت شد! برای دیدن دستورات، /help را وارد کنید.")
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        @app.route('/')
        def home():
            return "Telegram Bot is running!"
        
        @app.route('/webhook', methods=['POST'])
        def webhook():
            if request.method == 'POST':
                try:
                    update_data = request.get_json()
                    if application:
                        update = Update.de_json(update_data, application.bot)
                        application.process_update(update)
                    return jsonify({"status": "ok"}), 200
                except Exception as e:
                    logger.error(f"Webhook error: {e}")
                    return jsonify({"status": "error", "message": str(e)}), 500
            return jsonify({"status": "error"}), 400
        
        # Handle the request
        if 'httpMethod' in event:
            # AWS Lambda format
            if event['httpMethod'] == 'POST' and event.get('path') == '/webhook':
                with app.test_request_context('/webhook', method='POST', json=event.get('body', {})):
                    response = webhook()
                    return {
                        'statusCode': response[1],
                        'headers': {'Content-Type': 'application/json'},
                        'body': response[0].get_data(as_text=True)
                    }
            else:
                with app.test_request_context('/'):
                    response = home()
                    return {
                        'statusCode': 200,
                        'headers': {'Content-Type': 'text/html'},
                        'body': response
                    }
        else:
            # Direct call for testing
            return {'statusCode': 200, 'body': 'Bot initialized successfully'}
            
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }

# Flask app for direct execution
app = None

def get_app():
    """
    Get or create Flask app instance
    """
    global app
    if app is None:
        from flask import Flask, request, jsonify
        from telegram import Update
        from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
        
        app = Flask(__name__)
        
        # Get token
        TELEGRAM_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        
        if TELEGRAM_TOKEN:
            # Initialize application
            application = Application.builder().token(TELEGRAM_TOKEN).build()
            
            # Basic handlers
            async def start_command(update, context):
                await update.message.reply_text("🤖 ربات شما فعال است!")
            
            async def help_command(update, context):
                await update.message.reply_text("/start - شروع\n/help - راهنما\n/guess - بازی حدس عدد\n/rps - سنگ کاغذ قیچی\n/word - بازی کلمات\n/memory - بازی حافظه\n/random - بازی تصادفی\n/sticker <متن> - ساخت استیکر سریع\n/customsticker - استیکر ساز سفارشی")
            
            async def handle_message(update, context):
                if update.message and update.message.text:
                    await update.message.reply_text("🤖 ربات شما دریافت شد! برای دیدن دستورات، /help را وارد کنید.")
            
            # Add handlers
            application.add_handler(CommandHandler("start", start_command))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            logger.info("Basic handlers setup completed")
        
        @app.route('/')
        def home():
            return "Telegram Bot is running! All handlers are active."
        
        @app.route('/webhook', methods=['POST'])
        def webhook():
            if request.method == 'POST':
                try:
                    update_data = request.get_json()
                    logger.info(f"Received webhook data: {update_data}")
                    
                    if TELEGRAM_TOKEN and application:
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
            return jsonify({"status": "healthy", "handlers": "active"})
    
    return app

# Vercel serverless function handler
def handler(request):
    """
    Vercel serverless function handler
    """
    app = get_app()
    return app

# For direct execution
if __name__ == '__main__':
    app_instance = get_app()
    app_instance.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))