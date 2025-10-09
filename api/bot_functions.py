"""
توابع کمکی برای webhook - استخراج شده از bot.py
"""
import asyncio
import os
import sys
from typing import Dict, Any
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Add parent directory to path to import from main bot
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN باید در environment variables تنظیم شود.")

# Set BOT_TOKEN in environment before importing bot.py
os.environ["BOT_TOKEN"] = BOT_TOKEN

async def process_update(update_data: Dict[str, Any]) -> None:
    """
    پردازش update دریافتی از webhook
    """
    try:
        # Import router from main bot
        from bot import router
        
        bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        dp.include_router(router)
        
        # Create update object
        update = Update(**update_data)
        
        # Process the update
        await dp.feed_update(bot, update)
        
    except Exception as e:
        print(f"Error processing update: {e}")
        # Don't raise exception to prevent webhook retries
    finally:
        try:
            await bot.session.close()
        except:
            pass