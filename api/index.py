import json
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from utils import ServerlessCache, UserStateManager, validate_webhook_secret, get_error_response, is_valid_telegram_update

logger = logging.getLogger(__name__)

# Global variables for caching
_bot_application = None
_handlers_setup = False

def get_bot_application():
    """Get or create bot application with caching for serverless"""
    global _bot_application, _handlers_setup
    
    if _bot_application is None:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
            return None
            
        _bot_application = Application.builder().token(token).build()
        logger.info("Bot application created")
        
        # Setup handlers only once
        if not _handlers_setup:
            setup_bot_handlers(_bot_application)
            _handlers_setup = True
            logger.info("Bot handlers setup completed")
    
    return _bot_application

def setup_bot_handlers(application):
    """Setup bot handlers in a serverless-friendly way"""
    try:
        from handlers import setup_handlers
        
        # Create a new event loop for this operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(setup_handlers(application))
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error setting up handlers: {e}")
        # Continue without handlers if there's an error

def create_response(status_code, body, headers=None):
    """Create a standardized response for serverless functions"""
    response_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    if headers:
        response_headers.update(headers)
    
    return {
        'statusCode': status_code,
        'headers': response_headers,
        'body': json.dumps(body, ensure_ascii=False)
    }

def handler(event, context):
    """Main Vercel serverless function handler"""
    try:
        # Parse the request
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        headers = event.get('headers', {})
        
        logger.info(f"Received {http_method} request to {path}")
        
        # Health check endpoint
        if path == '/' and http_method == 'GET':
            return create_response(200, {
                'status': 'ok',
                'message': 'Telegram Bot is running!',
                'version': '2.0.0'
            })
        
        # Webhook endpoint
        if path == '/webhook' and http_method == 'POST':
            return handle_webhook(event)
        
        # Handle OPTIONS for CORS
        if http_method == 'OPTIONS':
            return create_response(200, {'status': 'ok'})
        
        # 404 for other routes
        return create_response(404, {
            'status': 'error',
            'message': 'Endpoint not found'
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in handler: {e}")
        return create_response(500, {
            'status': 'error',
            'message': 'Internal server error'
        })

def handle_webhook(event):
    """Handle Telegram webhook updates"""
    try:
        # Parse request body
        body = event.get('body', '')
        if isinstance(body, str):
            update_data = json.loads(body)
        else:
            update_data = body
        
        logger.info(f"Processing update: {update_data.get('update_id', 'unknown')}")
        
        # Get bot application
        application = get_bot_application()
        if not application:
            return create_response(500, {
                'status': 'error',
                'message': 'Bot not initialized'
            })
        
        # Process the update
        update = Update.de_json(update_data, application.bot)
        application.process_update(update)
        
        logger.info("Update processed successfully")
        return create_response(200, {
            'status': 'ok',
            'message': 'Update processed'
        })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return create_response(400, {
            'status': 'error',
            'message': 'Invalid JSON in request body'
        })
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return create_response(500, {
            'status': 'error',
            'message': str(e)
        })

# For local testing
if __name__ == '__main__':
    import sys
    from flask import Flask, request
    
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return handler({'httpMethod': 'GET', 'path': '/'}, None)
    
    @app.route('/webhook', methods=['POST'])
    def webhook():
        # Convert Flask request to Vercel event format
        event = {
            'httpMethod': 'POST',
            'path': '/webhook',
            'headers': dict(request.headers),
            'body': request.get_data(as_text=True)
        }
        return handler(event, None)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)