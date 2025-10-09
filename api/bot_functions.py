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

# Set BOT_TOKEN in environment before importing bot.py
BOT_TOKEN = os.getenv("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN باید در environment variables تنظیم شود.")

# Add parent directory to path to import from main bot
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set environment variable for bot.py
os.environ["BOT_TOKEN"] = BOT_TOKEN

# Global instances to avoid re-creation - این بخش کلیدی برای جلوگیری از خطای Router Attachment
_bot_instance = None
_dispatcher_instance = None

def get_bot_instance():
    """Get or create bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    return _bot_instance

def get_dispatcher_instance():
    """Get or create dispatcher instance with router"""
    global _dispatcher_instance
    if _dispatcher_instance is None:
        from bot import router
        _dispatcher_instance = Dispatcher()
        _dispatcher_instance.include_router(router)
    return _dispatcher_instance

async def process_update(update_data: Dict[str, Any]) -> None:
    """
    پردازش update دریافتی از webhook - بهینه شده برای جلوگیری از re-initialization
    این تابع از instance های سراسری استفاده می‌کنه تا از خطای Router Attachment جلوگیری بشه
    """
    try:
        # Get existing instances - از instance های قبلی استفاده می‌کنیم
        bot = get_bot_instance()
        dp = get_dispatcher_instance()
        
        # Create update object
        update = Update(**update_data)
        
        # Process the update
        await dp.feed_update(bot, update)
        
    except Exception as e:
        print(f"Error processing update: {e}")
        import traceback
        traceback.print_exc()
        # Don't raise exception to prevent webhook retries
        # حذف finally block برای بستن session - چون از instance سراسری استفاده می‌کنیم