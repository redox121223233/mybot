#!/usr/bin/env python3
"""
اسکریپت تنظیم webhook با URL واقعی
"""

import asyncio
import sys
import os
from api.bot_functions import set_webhook_url

def get_vercel_url():
    """دریافت URL واقعی از کاربر"""
    print("📝 لطفاً URL واقعی Vercel را وارد کنید:")
    print("مثال: https://mybot-redox.vercel.app/webhook")
    url = input("URL: ").strip()
    
    if not url.endswith('/webhook'):
        url += '/webhook'
    
    return url

async def main():
    """تنظیم webhook با URL واقعی"""
    try:
        print("🎯 تنظیم webhook با URL واقعی...")
        
        # URL را از کاربر بگیرید یا از environment
        webhook_url = os.getenv("WEBHOOK_URL")
        if not webhook_url:
            webhook_url = get_vercel_url()
        
        print(f"🔗 تنظیم webhook: {webhook_url}")
        
        success = await set_webhook_url(webhook_url)
        
        if success:
            print("✅ Webhook با موفقیت تنظیم شد!")
            print("🤖 ربات اکنون آماده دریافت پیام‌هاست!")
            print("💡 برای تست: به ربات پیام بدهید یا /start بزنید")
        else:
            print("❌ تنظیم webhook با خطا مواجه شد")
            
    except KeyboardInterrupt:
        print("\n❌ لغو شد")
    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    asyncio.run(main())