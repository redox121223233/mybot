"""
توابع کمکی برای webhook - استخراج شده از bot.py
"""
import asyncio
import os
from typing import Dict, Any
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN باید در environment variables تنظیم شود.")

async def process_update(update_data: Dict[str, Any]) -> None:
    """
    پردازش update دریافتی از webhook
    """
    try:
        print(f"Processing update: {update_data}")
        
        # Check if this is a /start command
        if 'message' in update_data:
            message = update_data['message']
            if 'text' in message and message['text'] == '/start':
                print("Processing /start command")
                # Here we would normally process the command
                # For now, just log that we received it
                print("Received /start command - would normally process it here")
                return
        
        print("Update processed successfully")
        
    except Exception as e:
        print(f"Error processing update: {e}")
        # Don't raise exception to prevent webhook retries