#!/usr/bin/env python3
"""
اسکریپت تنظیم webhook برای ربات تلگرام
"""

import asyncio
import os
import sys

# تنظیمات webhook - تنظیم BOT_TOKEN قبل از import bot
WEBHOOK_URL = "https://mybot-zx31.vercel.app"
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"

# تنظیم environment variable
os.environ["BOT_TOKEN"] = BOT_TOKEN

from bot import set_webhook_url

async def main():
    """تنظیم webhook"""
    try:
        print(f"🔧 تنظیم webhook برای ربات...")
        print(f"📡 URL: {WEBHOOK_URL}")
        
        await set_webhook_url(WEBHOOK_URL)
        
        print("✅ Webhook با موفقیت تنظیم شد!")
        print("🤖 ربات آماده دریافت پیام‌هاست!")
        
    except Exception as e:
        print(f"❌ خطا در تنظیم webhook: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())