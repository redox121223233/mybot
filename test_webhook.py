#!/usr/bin/env python3
"""
اسکریپت تست webhook برای ربات تلگرام
"""

import asyncio
import json
import requests

# تنظیمات
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"
WEBHOOK_URL = "https://mybot-zx31.vercel.app"

async def test_webhook():
    """تست webhook"""
    try:
        print("🧪 تست webhook ربات...")
        
        # بررسی اطلاعات webhook
        api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        response = requests.get(api_url)
        data = response.json()
        
        if data.get("ok"):
            webhook_info = data.get("result", {})
            print(f"📡 وضعیت webhook:")
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"   Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
            print(f"   IP address: {webhook_info.get('ip_address', 'Unknown')}")
            
            # بررسی آخرین خطاها
            last_error = webhook_info.get('last_error_message')
            if last_error:
                print(f"   ❌ آخرین خطا: {last_error}")
                print(f"   📅 زمان آخرین خطا: {webhook_info.get('last_error_date')}")
            else:
                print("   ✅ هیچ خطایی ثبت نشده!")
                
            # تست ارتباط با Vercel
            print(f"\n🔗 تست ارتباط با Vercel...")
            health_response = requests.get(f"{WEBHOOK_URL}/health", timeout=10)
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"   ✅ Vercel فعال است!")
                print(f"   📊 وضعیت: {health_data.get('status')}")
                print(f"   🤖 وضعیت ربات: {health_data.get('bot')}")
            else:
                print(f"   ⚠️ مشکل در ارتباط با Vercel: {health_response.status_code}")
                
        else:
            print(f"❌ خطا در دریافت اطلاعات webhook: {data.get('description')}")
            
    except Exception as e:
        print(f"❌ خطا در تست webhook: {e}")

if __name__ == "__main__":
    asyncio.run(test_webhook())