"""
سیستم کولد استارت بدون استفاده از cron job
- فقط در زمان دریافت اولین درخواست فعال می‌شود
- بدون استفاده از schedule یا timer
"""

import os
import sys
from typing import Dict, Any

# متغیر برای چک کردن اولین درخواست
_first_request = True

def handle_cold_start():
    """
    مدیریت کولد استارت - فقط در اولین درخواست
    بدون استفاده از cron job یا schedule
    """
    global _first_request
    
    if _first_request:
        _first_request = False
        print("🚀 Cold start detected - initializing...")
        
        try:
            # تنظیم webhook در اولین درخواست
            from api.bot_functions import set_webhook_url
            
            webhook_url = os.getenv("WEBHOOK_URL", "https://mybot-redox.vercel.app/webhook")
            bot_token = os.getenv("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0")
            
            if webhook_url and bot_token:
                print(f"🔗 Setting webhook: {webhook_url}")
                
                # استفاده از asyncio برای تنظیم webhook
                import asyncio
                try:
                    success = asyncio.run(set_webhook_url(webhook_url))
                    if success:
                        print("✅ Webhook set successfully on cold start")
                    else:
                        print("⚠️ Webhook setup failed on cold start")
                except Exception as e:
                    print(f"⚠️ Error setting webhook on cold start: {e}")
            
            print("✅ Cold start initialization complete")
            
        except Exception as e:
            print(f"⚠️ Error during cold start: {e}")
    
    else:
        print("📊 Normal request - no cold start needed")

def reset_cold_start_flag():
    """ریست فلگ برای تست‌های مجدد"""
    global _first_request
    _first_request = True
    print("🔄 Cold start flag reset")