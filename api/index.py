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
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
    # Create a dummy application for testing
    application = None
else:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

# Import and setup handlers
try:
    from handlers import setup_handlers
    import asyncio
    
    def setup_bot_handlers():
        """Setup bot handlers in a non-async way"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(setup_handlers(application))
        finally:
            loop.close()
    
    if application:
        setup_bot_handlers()
        logger.info("Bot handlers setup completed")
except Exception as e:
    logger.error(f"Error setting up handlers: {e}")

@app.route('/')
def home():
    return "Telegram Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if not application:
        return jsonify({"status": "error", "message": "Bot not initialized"}), 500
        
    if request.method == 'POST':
        try:
            update = Update.de_json(request.get_json(), application.bot)
            application.process_update(update)
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error"}), 400

# Vercel serverless function handler
def handler(request):
    """Main handler for Vercel serverless functions"""
    with app.app_context():
        # Convert Vercel request to Flask request
        with app.test_request_context(
            path=request.path,
            method=request.method,
            data=request.get_data(),
            headers=dict(request.headers),
            query_string=request.query_string.decode('utf-8')
        ):
            # Route to the appropriate endpoint
            if request.path == '/' and request.method == 'GET':
                response = home()
            elif request.path == '/webhook' and request.method == 'POST':
                response = webhook()
            else:
                response = jsonify({"status": "not_found"}), 404
            
            # Convert Flask response to Vercel response
            if isinstance(response, tuple):
                return response
            else:
                return response.data, response.status_code, dict(response.headers)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))