#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
اسکریپت راه‌اندازی ربات استیکر
این اسکریپت همه فایل‌های مورد نیاز را ایجاد می‌کند
"""

import os
import json
import time
from pathlib import Path

def create_directory_structure():
    """ایجاد ساختار پوشه‌ها"""
    directories = [
        "fonts",
        "templates", 
        "backups",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ پوشه {directory} ایجاد شد")

def create_json_files():
    """ایجاد فایل‌های JSON اولیه"""
    
    # اگر فایل‌ها وجود دارند، پشتیبان‌گیری کن
    json_files = [
        "users.json",
        "subscriptions.json", 
        "user_packs.json",
        "pending_payments.json",
        "feedback_data.json",
        "bot_settings.json"
    ]
    
    for filename in json_files:
        if os.path.exists(filename):
            backup_name = f"{filename}.backup_{int(time.time())}"
            os.rename(filename, backup_name)
            print(f"📦 پشتیبان‌گیری: {filename} -> {backup_name}")
    
    # ایجاد فایل‌های جدید
    files_data = {
        "users.json": {},
        "subscriptions.json": {},
        "user_packs.json": {},
        "pending_payments.json": {},
        "feedback_data.json": {},
        "bot_settings.json": {
            "bot_version": "2.0.0",
            "last_backup": time.time(),
            "maintenance_mode": False,
            "max_file_size_mb": 20,
            "max_stickers_per_day_free": 5,
            "default_language": "fa",
            "auto_backup_enabled": True,
            "backup_interval_hours": 24,
            "keep_backups_days": 7,
            "image_quality_settings": {
                "small_file_quality": 90,
                "medium_file_quality": 85,
                "large_file_quality": 75
            },
            "file_size_thresholds": {
                "small_mb": 2,
                "medium_mb": 5,
                "large_mb": 10
            },
            "compression_settings": {
                "max_image_size": 2048,
                "sticker_size": 512,
                "png_compress_level": 9,
                "webp_quality": 85
            },
            "admin_settings": {
                "admin_id": 6053579919,
                "support_username": "@onedaytoalive",
                "broadcast_enabled": True,
                "stats_enabled": True
            },
            "subscription_plans": {
                "1month": {"price": 100, "days": 30, "title": "یک ماهه"},
                "3months": {"price": 250, "days": 90, "title": "سه ماهه"},
                "12months": {"price": 350, "days": 365, "title": "یک ساله"}
            },
            "payment_info": {
                "card_number": "1234-5678-9012-3456",
                "card_name": "نام صاحب کارت"
            },
            "channel_settings": {
                "required_channel": "@YourChannel",
                "membership_required": True
            },
            "feature_flags": {
                "premium_features_enabled": True,
                "feedback_system_enabled": True,
                "template_system_enabled": True,
                "advanced_design_enabled": True
            },
            "limits": {
                "max_pack_name_length": 64,
                "max_text_length": 200,
                "max_packs_per_user": 50,
                "max_stickers_per_pack": 120
            },
            "performance": {
                "request_timeout": 30,
                "image_processing_timeout": 60,
                "ffmpeg_timeout": 120,
                "max_concurrent_users": 100
            }
        }
    }
    
    for filename, data in files_data.items():
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ فایل {filename} ایجاد شد")

def create_env_template():
    """ایجاد فایل نمونه متغیرهای محیطی"""
    env_content = """# متغیرهای محیطی ربات استیکر
# این فایل را کپی کنید و نام آن را .env بگذارید

# اطلاعات ربات (اجباری)
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=your_bot_username
APP_URL=https://your-app-url.com

# کانال اجباری
CHANNEL_LINK=@your_channel

# اطلاعات پرداخت
CARD_NUMBER=1234-5678-9012-3456
CARD_NAME=نام صاحب کارت

# تنظیمات اختیاری
PORT=8080
WEBHOOK_SECRET=your_secret_key

# مسیر فونت‌ها (اختیاری)
FONTS_DIR=./fonts

# تنظیمات دیتابیس (اختیاری)
DATA_DIR=./data
BACKUP_DIR=./backups
"""
    
    with open(".env.example", 'w', encoding='utf-8') as f:
        f.write(env_content)
    print("✅ فایل .env.example ایجاد شد")

def create_requirements():
    """ایجاد فایل requirements.txt"""
    requirements = """flask==2.3.3
requests==2.31.0
pillow==10.0.1
waitress==2.1.2
arabic-reshaper==3.0.0
python-bidi==0.4.2
"""
    
    with open("requirements.txt", 'w') as f:
        f.write(requirements)
    print("✅ فایل requirements.txt ایجاد شد")

def create_run_script():
    """ایجاد اسکریپت اجرا"""
    
    # اسکریپت برای ویندوز
    windows_script = """@echo off
echo شروع ربات استیکر...
python bot.py
pause
"""
    
    with open("run_bot.bat", 'w', encoding='utf-8') as f:
        f.write(windows_script)
    print("✅ فایل run_bot.bat ایجاد شد")
    
    # اسکریپت برای لینوکس/مک
    unix_script = """#!/bin/bash
echo "شروع ربات استیکر..."
python3 bot.py
"""
    
    with open("run_bot.sh", 'w', encoding='utf-8') as f:
        f.write(unix_script)
    
    # اجازه اجرا برای لینوکس/مک
    try:
        os.chmod("run_bot.sh", 0o755)
    except:
        pass
    
    print("✅ فایل run_bot.sh ایجاد شد")

def check_dependencies():
    """بررسی وابستگی‌ها"""
    print("\n🔍 بررسی وابستگی‌ها...")
    
    required_modules = [
        "flask",
        "requests", 
        "PIL",
        "waitress",
        "arabic_reshaper",
        "bidi"
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            if module == "PIL":
                import PIL
            else:
                __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - نصب نشده")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n⚠️  برای نصب وابستگی‌های مفقود:")
        print("pip install -r requirements.txt")
    else:
        print("\n✅ همه وابستگی‌ها نصب شده‌اند")

def main():
    """تابع اصلی راه‌اندازی"""
    print("🚀 راه‌اندازی ربات استیکر")
    print("=" * 40)
    
    # ایجاد ساختار پوشه‌ها
    print("\n📁 ایجاد پوشه‌ها...")
    create_directory_structure()
    
    # ایجاد فایل‌های JSON
    print("\n📄 ایجاد فایل‌های داده...")
    create_json_files()
    
    # ایجاد فایل‌های کمکی
    print("\n⚙️  ایجاد فایل‌های تنظیمات...")
    create_env_template()
    create_requirements()
    create_run_script()
    
    # بررسی وابستگی‌ها
    check_dependencies()
    
    print("\n" + "=" * 40)
    print("✅ راه‌اندازی کامل شد!")
    print("\n📋 مراحل بعدی:")
    print("1. فایل .env.example را کپی کنید و نام آن را .env بگذارید")
    print("2. اطلاعات ربات را در فایل .env وارد کنید")
    print("3. فونت‌های فارسی را در پوشه fonts قرار دهید")
    print("4. ربات را با python bot.py اجرا کنید")
    print("\n🎉 موفق باشید!")

if __name__ == "__main__":
    main()