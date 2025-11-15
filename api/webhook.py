#!/usr/bin/env python3

"""
Vercel Serverless Function for Telegram Bot Webhook
"""

import os
import json
import logging
from telegram import Update, Bot
from telegram.ext import Application

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")

async def handle_update(update: Update, application: Application):
    """Handle Telegram update"""
    try:
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")

def handler(request):
    """Vercel serverless function handler"""
    try:
        # Log the request
        logger.info(f"Received request: {request.method} {request.url}")
        
        # Handle webhook requests
        if request.method == 'POST':
            try:
                # Parse the update
                update_data = request.get_json()
                if not update_data:
                    logger.error("No JSON data received")
                    return {"error": "No JSON data"}, 400
                
                logger.info(f"Received update: {update_data}")
                
                # Create bot instance
                bot = Bot(token=BOT_TOKEN)
                
                # Create application
                application = Application.builder().token(BOT_TOKEN).build()
                
                # Import and setup handlers from main bot file
                import sys
                sys.path.append('/var/task')
                try:
                    from index import setup_handlers, start_command, help_command, create_sticker_command
                    setup_handlers(application)
                    
                    # Create Update object
                    update = Update.de_json(update_data, bot)
                    
                    # Process the update
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(handle_update(update, application))
                    loop.close()
                    
                    return {"status": "ok"}, 200
                    
                except ImportError as e:
                    logger.error(f"Cannot import bot handlers: {e}")
                    # Fallback: handle basic commands here
                    update = Update.de_json(update_data, bot)
                    
                    if update.message and update.message.text == '/start':
                        await bot.send_message(
                            chat_id=update.effective_chat.id,
                            text="🎨 Welcome to the Sticker Bot!\n\nSend me an image and text to create a custom sticker."
                        )
                        return {"status": "ok"}, 200
                    
                    return {"status": "ok"}, 200
                    
            except Exception as e:
                logger.error(f"Error processing webhook: {e}")
                return {"error": str(e)}, 500
        
        # Handle health check
        elif request.method == 'GET':
            return {"status": "Bot is running"}, 200
        
        else:
            return {"error": "Method not allowed"}, 405
            
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {"error": str(e)}, 500

# For Vercel deployment
def lambda_handler(event, context):
    """AWS Lambda handler (for Vercel compatibility)"""
    return handler(event)