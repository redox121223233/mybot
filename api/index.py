#!/usr/bin/env python3

"""
Enhanced Telegram Sticker Bot - Fixed Version
Fixed NoneType error for webhook handling
"""

import os
import json
import logging
import asyncio
import tempfile
import io
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Vercel
app = Flask(__name__)

# Bot Configuration
BOT_USERNAME = "@matnsticker_bot"
ADMIN_ID = 6053579919
SUPPORT_USERNAME = "@onedaytoalive"
ADVANCED_DAILY_LIMIT = 3
REQUIRED_CHANNEL = "@redoxbot_sticker"

# Data Storage
USERS: Dict[int, Dict[str, Any]] = {}
USER_LIMITS: Dict[int, Dict[str, Any]] = {}
STICKER_PACKS: Dict[str, Dict[str, Any]] = {}

# Global bot and application variables
bot = None
application = None

def load_data():
    """Load data from files"""
    global USERS, USER_LIMITS, STICKER_PACKS
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r') as f:
                USERS = json.load(f)
        if os.path.exists('limits.json'):
            with open('limits.json', 'r') as f:
                USER_LIMITS = json.load(f)
        if os.path.exists('packs.json'):
            with open('packs.json', 'r') as f:
                STICKER_PACKS = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_data():
    """Save data to files"""
    try:
        with open('users.json', 'w') as f:
            json.dump(USERS, f)
        with open('limits.json', 'w') as f:
            json.dump(USER_LIMITS, f)
        with open('packs.json', 'w') as f:
            json.dump(STICKER_PACKS, f)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def initialize_bot():
    """Initialize bot application"""
    global bot, application
    
    # Return existing bot if already initialized
    if application is not None and bot is not None:
        return bot
        
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables")
        return None
    
    try:
        application = Application.builder().token(bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin))
        application.add_handler(CommandHandler("help", help_cmd))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        bot = type('Bot', (), {'application': application})()
        
        # Set webhook
        webhook_url = os.environ.get("VERCEL_URL")
        if webhook_url:
            full_url = f"https://{webhook_url}/api/webhook"
            try:
                asyncio.run(application.bot.set_webhook(full_url))
                logger.info("Webhook set successfully")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")
        
        logger.info("Bot initialized successfully")
        return bot
        
    except Exception as e:
        logger.error(f"Error initializing bot: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name}! به ربات استیکر ساز خوش آمدید.\n"
        "برای استفاده از ربات، یک عکس برایم بفرستید."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    await update.message.reply_text(
        "راهنمای ربات:\n"
        "/start - شروع ربات\n"
        "/help - نمایش راهنما\n"
        "عکس بفرستید تا استیکر بسازم"
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command handler"""
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("این دستور فقط برای مدیر است!")
        return
    
    await update.message.reply_text("پنل مدیریت:\nربات فعال و آماده به کار است.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    await update.message.reply_text("عکس دریافت شد. در حال پردازش...")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    await update.message.reply_text("لطفا عکس بفرستید تا استیکر بسازم.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

# Flask routes
@app.route('/')
def home():
    """Home page redirect"""
    return "Enhanced Sticker Bot is running!"

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Webhook handler for Telegram bot - FIXED VERSION"""
    try:
        # Initialize bot if not already done
        current_bot = initialize_bot()
        if current_bot is None:
            logger.error("Bot initialization failed")
            return "Bot initialization failed", 500
            
        if request.is_json:
            update_data = request.get_json()
            logger.info(f"Received update: {update_data}")
            
            # Create update object properly
            update = Update.de_json(update_data, current_bot.application.bot)
            
            # Process the update
            asyncio.run(current_bot.application.process_update(update))
            
            return "OK"
        else:
            return "Invalid request", 400
            
    except AttributeError as e:
        logger.error(f"Attribute error in webhook: {e}")
        return f"Webhook error: {str(e)}", 500
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return f"Webhook error: {str(e)}", 500

def main():
    """Main function"""
    # Load data
    load_data()
    
    # Initialize bot
    initialize_bot()
    
    # Start Flask
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port)

# Vercel serverless handler
def handler(request):
    """Vercel serverless function handler"""
    # Load data if not already loaded
    if not hasattr(handler, 'data_loaded'):
        load_data()
        handler.data_loaded = True
    
    # Initialize bot if not already initialized
    if not hasattr(handler, 'bot_initialized'):
        initialize_bot()
        handler.bot_initialized = True
    
    # Handle the request
    from flask import Flask
    global app
    with app.app_context():
        if request.method == 'POST' and request.path == '/api/webhook':
            return webhook()
        elif request.path == '/':
            return home()
        else:
            return "Not found", 404

if __name__ == "__main__":
    main()