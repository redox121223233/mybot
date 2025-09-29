#!/usr/bin/env python3
"""
اسکریپت راه‌اندازی ربات برای Vercel
این اسکریپت به شما کمک می‌کند تا ربات را برای استقرار روی Vercel آماده کنید.
"""

import os
import json
import requests
import sys

def check_requirements():
    """بررسی وجود فایل‌های مورد نیاز"""
    required_files = [
        'vercel.json',
        'requirements.txt',
        'api/webhook.py',
        'api/index.py',
        'api/health.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ فایل‌های زیر موجود نیستند:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ تمام فایل‌های مورد نیاز موجود هستند")
    return True

def get_bot_info(bot_token):
    """دریافت اطلاعات ربات"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data['result']
                return {
                    'username': bot_info.get('username'),
                    'first_name': bot_info.get('first_name'),
                    'id': bot_info.get('id')
                }
    except Exception as e:
        print(f"❌ خطا در دریافت اطلاعات ربات: {e}")
    
    return None

def validate_bot_token(bot_token):
    """اعتبارسنجی توکن ربات"""
    if not bot_token or bot_token == "YOUR_BOT_TOKEN_HERE":
        print("❌ توکن ربات معتبر نیست")
        return False
    
    bot_info = get_bot_info(bot_token)
    if bot_info:
        print(f"✅ ربات معتبر است: @{bot_info['username']} ({bot_info['first_name']})")
        return True
    else:
        print("❌ توکن ربات نامعتبر است")
        return False

def create_env_example():
    """ایجاد فایل نمونه متغیرهای محیطی"""
    env_content = """# متغیرهای محیطی برای Vercel
# این فایل را در تنظیمات Vercel اضافه کنید

# اجباری
BOT_TOKEN=your_bot_token_here
WEBHOOK_SECRET=your_webhook_secret_here

# اختیاری
BOT_USERNAME=your_bot_username
CHANNEL_LINK=@your_channel
ADMIN_ID=your_admin_id
SUPPORT_ID=@your_support_username
APP_URL=https://your-project.vercel.app
"""
    
    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ فایل .env.example ایجاد شد")

def setup_webhook_url(bot_token, app_url, webhook_secret):
    """تنظیم webhook تلگرام"""
    if not app_url:
        print("❌ URL اپلیکیشن مشخص نشده است")
        return False
    
    webhook_url = f"{app_url.rstrip('/')}/webhook/{webhook_secret}"
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json={
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                print(f"✅ Webhook تنظیم شد: {webhook_url}")
                return True
            else:
                print(f"❌ خطا در تنظیم webhook: {data.get('description')}")
        else:
            print(f"❌ خطا در درخواست: {response.status_code}")
    
    except Exception as e:
        print(f"❌ خطا در تنظیم webhook: {e}")
    
    return False

def check_webhook_status(bot_token):
    """بررسی وضعیت webhook"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo")
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                webhook_info = data['result']
                print("\n📊 وضعیت Webhook:")
                print(f"   URL: {webhook_info.get('url', 'تنظیم نشده')}")
                print(f"   آخرین خطا: {webhook_info.get('last_error_message', 'ندارد')}")
                print(f"   تعداد خطاها: {webhook_info.get('last_error_date', 0)}")
                return True
    except Exception as e:
        print(f"❌ خطا در بررسی webhook: {e}")
    
    return False

def main():
    """تابع اصلی"""
    print("🚀 راه‌اندازی ربات برای Vercel")
    print("=" * 40)
    
    # بررسی فایل‌های مورد نیاز
    if not check_requirements():
        sys.exit(1)
    
    # ایجاد فایل نمونه
    create_env_example()
    
    # دریافت اطلاعات از کاربر
    print("\n📝 لطفاً اطلاعات زیر را وارد کنید:")
    
    bot_token = input("توکن ربات: ").strip()
    if not validate_bot_token(bot_token):
        sys.exit(1)
    
    webhook_secret = input("کلید امنیتی webhook (اختیاری): ").strip()
    if not webhook_secret:
        webhook_secret = "secret"
    
    app_url = input("URL پروژه Vercel (اختیاری): ").strip()
    
    print("\n🔧 تنظیمات:")
    print(f"   توکن ربات: {bot_token[:10]}...")
    print(f"   کلید webhook: {webhook_secret}")
    print(f"   URL پروژه: {app_url or 'تنظیم نشده'}")
    
    # تنظیم webhook اگر URL موجود باشد
    if app_url and bot_token:
        setup_webhook_url(bot_token, app_url, webhook_secret)
        check_webhook_status(bot_token)
    
    print("\n✅ راه‌اندازی کامل شد!")
    print("\n📋 مراحل بعدی:")
    print("1. کد را به GitHub push کنید")
    print("2. پروژه را به Vercel متصل کنید")
    print("3. متغیرهای محیطی را در Vercel تنظیم کنید")
    print("4. پس از deploy، webhook را تنظیم کنید")
    print("5. ربات را در تلگرام تست کنید")

if __name__ == "__main__":
    main()