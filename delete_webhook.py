#!/usr/bin/env python3
"""
اسکریپت حذف webhook برای ربات تلگرام
"""

import asyncio
from aiogram import Bot
import os

BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"

async def delete_webhook():
    """حذف webhook"""
    try:
        bot = Bot(token=BOT_TOKEN)
        
        print("🗑️ حذف webhook...")
        await bot.delete_webhook(drop_pending_updates=True)
        
        print("✅ Webhook با موفقیت حذف شد!")
        print("🔄 ربات به حالت polling برگشته است!")
        
    except Exception as e:
        print(f"❌ خطا در حذف webhook: {e}")

if __name__ == "__main__":
    asyncio.run(delete_webhook())