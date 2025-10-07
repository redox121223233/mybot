#!/usr/bin/env python3
"""
اسکریپت دیباگ کامل webhook
"""

import asyncio
import requests
import os
from api.bot_functions import set_webhook_url

# تنظیمات
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"
WEBHOOK_URL = "https://mybot-xyz.vercel.app/webhook"

def test_telegram_webhook():
    """تست وضعیت webhook در Telegram"""
    try:
        print("🔍 بررسی وضعیت webhook در Telegram...")
        
        # بررسی وضعیت webhook
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
        data = response.json()
        
        if data.get("ok"):
            info = data.get("result", {})
            print(f"📡 وضعیت webhook:")
            print(f"   URL: {info.get('url', 'Not set')}")
            print(f"   Pending updates: {info.get('pending_update_count', 0)}")
            print(f"   IP address: {info.get('ip_address', 'Unknown')}")
            print(f"   Last error: {info.get('last_error_message', 'None')}")
            print(f"   Last error date: {info.get('last_error_date', 'None')}")
            
            # بررسی آیا webhook تنظیم شده
            if info.get('url'):
                print("✅ Webhook تنظیم شده")
            else:
                print("❌ Webhook تنظیم نشده")
                
        else:
            print(f"❌ خطا در دریافت اطلاعات: {data.get('description')}")
            
    except Exception as e:
        print(f"❌ خطا در تست: {e}")

async def reset_webhook():
    """ریست و تنظیم مجدد webhook"""
    try:
        print("🔄 ریست و تنظیم مجدد webhook...")
        success = await set_webhook_url(WEBHOOK_URL)
        
        if success:
            print("✅ Webhook با موفقیت تنظیم شد")
        else:
            print("❌ تنظیم webhook با خطا مواجه شد")
            
    except Exception as e:
        print(f"❌ خطا در تنظیم: {e}")

if __name__ == "__main__":
    test_telegram_webhook()
    asyncio.run(reset_webhook())