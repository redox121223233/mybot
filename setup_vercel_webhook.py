#!/usr/bin/env python3
"""
اسکریپت تنظیم webhook برای Vercel deployment
"""

import asyncio
import os
from api.bot_functions import set_webhook_url

# تنظیمات - URL را با مقدار واقعی جایگزین کنید
# بعد از deployment در Vercel، URL را به صورت زیر تنظیم کنید:
WEBHOOK_URL = "https://mybot-redox.vercel.app/webhook"
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"

async def main():
    """تنظیم webhook"""
    try:
        print("🔧 تنظیم webhook برای ربات...")
        print(f"📡 URL: {WEBHOOK_URL}")
        
        success = await set_webhook_url(WEBHOOK_URL)
        
        if success:
            print("✅ Webhook با موفقیت تنظیم شد!")
            print("🤖 ربات آماده دریافت پیام‌هاست!")
        else:
            print("❌ تنظیم webhook با خطا مواجه شد")
            
    except Exception as e:
        print(f"❌ خطا در تنظیم webhook: {e}")

if __name__ == "__main__":
    asyncio.run(main())