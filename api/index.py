import logging
import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Telegram bot
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Import handlers
try:
    from handlers import *
    setup_handlers(application)
    logger.info("Handlers loaded successfully")
except ImportError as e:
    logger.error(f"Error importing handlers: {e}")

# FastAPI version (for Vercel)
try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    
    app = FastAPI(title="Telegram Sticker Bot API")
    
    @app.get("/")
    async def root():
        return {"message": "Telegram Bot is running!"}
    
    @app.post("/webhook")
    async def webhook(request: Request):
        """Handle Telegram webhook updates"""
        try:
            update_data = await request.json()
            logger.info(f"Received update: {update_data}")
            
            # Process the update
            update = Update.de_json(update_data, application.bot)
            
            # Update user information
            from user_manager import user_manager
            user_manager.update_user(update)
            
            # Check rate limiting
            from security import security_manager
            user_id = update.effective_user.id if update.effective_user else None
            
            if user_id and not security_manager.check_rate_limit(user_id):
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded"}
                )
            
            await application.process_update(update)
            
            return JSONResponse(
                status_code=200,
                content={"status": "ok"}
            )
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )
    
    logger.info("FastAPI app initialized successfully")
    
except ImportError:
    # Flask version (fallback)
    try:
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        
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
        
        logger.info("Flask app initialized successfully")
        
    except ImportError:
        logger.error("Neither FastAPI nor Flask is available!")
        app = None