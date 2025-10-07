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

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN باید در environment variables تنظیم شود.")

async def process_update(update_data: Dict[str, Any]) -> None:
    """
    پردازش update دریافتی از webhook
    """
    try:
        bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        
        # Import router from main bot
        from bot import router
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

async def set_webhook_url(webhook_url: str) -> bool:
    """
    تنظیم webhook برای ربات
    """
    try:
        bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # Delete existing webhook
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Set new webhook
        await bot.set_webhook(url=webhook_url)
        
        print(f"✅ Webhook set successfully to: {webhook_url}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to set webhook: {e}")
        return False
    finally:
        try:
            await bot.session.close()
        except:
            pass