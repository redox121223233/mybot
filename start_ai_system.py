#!/usr/bin/env python3
"""
اسکریپت راه‌اندازی خودکار سیستم هوش مصنوعی
"""

import os
import sys
import time
import subprocess
import threading
import requests
from pathlib import Path

def check_dependencies():
    """بررسی وابستگی‌های مورد نیاز"""
    print("🔍 بررسی وابستگی‌ها...")
    
    required_packages = ['flask', 'requests', 'waitress']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} نصب شده")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} نصب نشده")
    
    if missing_packages:
        print(f"\n📦 نصب پکیج‌های مورد نیاز: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ تمام پکیج‌ها نصب شدند")
        except subprocess.CalledProcessError:
            print("❌ خطا در نصب پکیج‌ها")
            return False
    
    return True

def check_files():
    """بررسی وجود فایل‌های مورد نیاز"""
    print("\n📁 بررسی فایل‌ها...")
    
    required_files = [
        'ai_control_server.py',
        'ai_integration.py',
        'bot.py'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} موجود است")
        else:
            missing_files.append(file)
            print(f"❌ {file} موجود نیست")
    
    if missing_files:
        print(f"\n❌ فایل‌های مورد نیاز موجود نیست: {', '.join(missing_files)}")
        return False
    
    return True

def setup_environment():
    """تنظیم متغیرهای محیطی"""
    print("\n🔧 تنظیم متغیرهای محیطی...")
    
    env_vars = {
        'AI_CONTROL_URL': 'http://localhost:5000',
        'AI_CONTROL_SECRET': 'ai_secret_2025',
        'AI_CONTROL_PORT': '5000'
    }
    
    for key, default_value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value
            print(f"✅ {key} = {default_value}")
        else:
            print(f"✅ {key} = {os.environ[key]} (از قبل تنظیم شده)")

def start_ai_control_server():
    """راه‌اندازی سرور کنترل هوش مصنوعی"""
    print("\n🚀 راه‌اندازی سرور کنترل هوش مصنوعی...")
    
    try:
        # اجرای سرور در thread جداگانه
        def run_server():
            subprocess.run([sys.executable, 'ai_control_server.py'])
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # صبر برای راه‌اندازی سرور
        print("⏳ صبر برای راه‌اندازی سرور...")
        time.sleep(3)
        
        # تست اتصال
        for attempt in range(5):
            try:
                response = requests.get('http://localhost:5000/health', timeout=2)
                if response.status_code == 200:
                    print("✅ سرور کنترل با موفقیت راه‌اندازی شد")
                    return True
            except:
                print(f"⏳ تلاش {attempt + 1}/5...")
                time.sleep(2)
        
        print("❌ خطا در راه‌اندازی سرور کنترل")
        return False
        
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی سرور: {e}")
        return False

def test_ai_system():
    """تست سیستم هوش مصنوعی"""
    print("\n🧪 تست سیستم هوش مصنوعی...")
    
    try:
        # تست API وضعیت
        response = requests.get('http://localhost:5000/api/check', timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = "فعال" if data.get('active') else "غیرفعال"
            print(f"✅ وضعیت هوش مصنوعی: {status}")
            
            # تست تغییر وضعیت
            toggle_response = requests.post('http://localhost:5000/api/toggle', timeout=5)
            if toggle_response.status_code == 200:
                print("✅ تست تغییر وضعیت موفق")
                return True
            else:
                print("❌ خطا در تست تغییر وضعیت")
                return False
        else:
            print("❌ خطا در دریافت وضعیت")
            return False
            
    except Exception as e:
        print(f"❌ خطا در تست سیستم: {e}")
        return False

def show_status():
    """نمایش وضعیت سیستم"""
    print("\n" + "="*50)
    print("📊 وضعیت سیستم هوش مصنوعی")
    print("="*50)
    
    try:
        response = requests.get('http://localhost:5000/api/ai-status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"🤖 وضعیت: {'فعال ✅' if data.get('active') else 'غیرفعال ❌'}")
            print(f"⏰ آخرین به‌روزرسانی: {data.get('formatted_time', 'نامشخص')}")
            print(f"👤 به‌روزرسانی شده توسط: {data.get('updated_by', 'نامشخص')}")
        else:
            print("❌ خطا در دریافت وضعیت")
    except:
        print("❌ سرور در دسترس نیست")
    
    print(f"🌐 پنل وب: http://localhost:5000")
    print(f"🔗 API: http://localhost:5000/api/check")
    print("="*50)

def main():
    """تابع اصلی"""
    print("🚀 راه‌اندازی سیستم هوش مصنوعی")
    print("="*50)
    
    # بررسی وابستگی‌ها
    if not check_dependencies():
        print("❌ خطا در بررسی وابستگی‌ها")
        return False
    
    # بررسی فایل‌ها
    if not check_files():
        print("❌ خطا در بررسی فایل‌ها")
        return False
    
    # تنظیم محیط
    setup_environment()
    
    # راه‌اندازی سرور
    if not start_ai_control_server():
        print("❌ خطا در راه‌اندازی سرور")
        return False
    
    # تست سیستم
    if not test_ai_system():
        print("❌ خطا در تست سیستم")
        return False
    
    # نمایش وضعیت
    show_status()
    
    print("\n✅ سیستم هوش مصنوعی با موفقیت راه‌اندازی شد!")
    print("\n💡 نکات مهم:")
    print("• سرور کنترل در پس‌زمینه اجرا می‌شود")
    print("• برای توقف، Ctrl+C را فشار دهید")
    print("• پنل وب در http://localhost:5000 در دسترس است")
    print("• حالا می‌توانید ربات را راه‌اندازی کنید: python bot.py")
    
    try:
        print("\n⏳ سرور در حال اجرا... (Ctrl+C برای توقف)")
        while True:
            time.sleep(10)
            # بررسی دوره‌ای سلامت سرور
            try:
                requests.get('http://localhost:5000/health', timeout=2)
            except:
                print("⚠️ سرور قطع شده، تلاش برای راه‌اندازی مجدد...")
                if not start_ai_control_server():
                    print("❌ خطا در راه‌اندازی مجدد")
                    break
    except KeyboardInterrupt:
        print("\n🛑 سیستم متوقف شد")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)