#!/usr/bin/env python3
"""
فایل اصلی برای اجرای محلی ربات
برای اجرا: python main.py
"""

import os
import logging
from telegram import Update
from telegram.ext import Application

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """تابع اصلی برای اجرای ربات"""
    # خواندن توکن از متغیر محیطی
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN تنظیم نشده است!")
        print("لطفاً ابتدا توکن ربات را تنظیم کنید:")
        print("export TELEGRAM_BOT_TOKEN='YOUR_BOT_TOKEN_HERE'")
        return
    
    # ایجاد اپلیکیشن
    application = Application.builder().token(token).build()
    
    # تنظیم handlerها
    from handlers import setup_handlers
    import asyncio
    asyncio.run(setup_handlers(application))
    
    # اجرای ربات
    print("🤖 ربات بازی و استیکر ساز با موفقیت اجرا شد!")
    print("📋 دستورات موجود:")
    print("  /start - شروع و منوی اصلی")
    print("  /help - راهنمای کامل")
    print("  /guess - بازی حدس عدد")
    print("  /rps - سنگ کاغذ قیچی")
    print("  /word - بازی کلمات")
    print("  /memory - بازی حافظه")
    print("  /random - بازی تصادفی")
    print("  /sticker <متن> - ساخت استیکر سریع")
    print("  /customsticker - استیکر ساز سفارشی")
    print()
    
    application.run_polling()

if __name__ == '__main__':
    main()