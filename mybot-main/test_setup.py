#!/usr/bin/env python3
"""
اسکریپت تست تنظیمات ربات قبل از اجرا
"""

import os
import sys
import subprocess

def check_python():
    """بررسی نسخه پایتون"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ نسخه Python باید 3.9 یا بالاتر باشد")
        print(f"   نسخه فعلی: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_ffmpeg():
    """بررسی نصب FFmpeg"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FFmpeg نصب شده است")
            return True
    except FileNotFoundError:
        pass
    print("⚠️  FFmpeg نصب نیست - استیکرهای ویدیویی کار نخواهند کرد")
    return False

def check_env():
    """بررسی فایل .env"""
    if not os.path.exists('.env'):
        print("❌ فایل .env وجود ندارد")
        print("   یک فایل .env با محتوای زیر ایجاد کنید:")
        print("   BOT_TOKEN=your_token_here")
        return False

    with open('.env', 'r') as f:
        content = f.read()

    if 'BOT_TOKEN' not in content or 'your_token_here' in content or 'BOT_TOKEN=' in content.split('\n')[0] and len(content.split('\n')[0].split('=')[1].strip()) < 10:
        print("❌ BOT_TOKEN در فایل .env تنظیم نشده است")
        return False

    print("✅ فایل .env موجود است و BOT_TOKEN تنظیم شده")
    return True

def check_libraries():
    """بررسی نصب کتابخانه‌ها"""
    libraries = {
        'aiogram': 'aiogram',
        'PIL': 'Pillow',
        'arabic_reshaper': 'arabic-reshaper',
        'bidi': 'python-bidi'
    }

    missing = []
    for module, package in libraries.items():
        try:
            __import__(module)
            print(f"✅ {package} نصب شده است")
        except ImportError:
            print(f"❌ {package} نصب نیست")
            missing.append(package)

    if missing:
        print(f"\n📥 برای نصب کتابخانه‌های کم:")
        print(f"   pip3 install {' '.join(missing)}")
        return False

    return True

def check_fonts():
    """بررسی فونت‌ها"""
    fonts_dir = 'fonts'

    if not os.path.exists(fonts_dir):
        print(f"❌ پوشه {fonts_dir} وجود ندارد")
        return False

    fonts = [f for f in os.listdir(fonts_dir) if f.endswith(('.ttf', '.otf'))]

    if not fonts:
        print(f"⚠️  هیچ فونتی در پوشه {fonts_dir} یافت نشد")
        print(f"   راهنما: {fonts_dir}/README.md")
        return False

    print(f"✅ {len(fonts)} فونت در پوشه fonts یافت شد:")
    for font in fonts[:5]:  # نمایش 5 فونت اول
        print(f"   - {font}")
    if len(fonts) > 5:
        print(f"   ... و {len(fonts) - 5} فونت دیگر")

    return True

def check_templates():
    """بررسی پوشه templates"""
    templates_dir = 'templates'

    if not os.path.exists(templates_dir):
        print(f"⚠️  پوشه {templates_dir} وجود ندارد - در حال ساخت...")
        os.makedirs(templates_dir)

    # بررسی وجود فایل gradient
    has_gradient = any(
        os.path.exists(os.path.join(templates_dir, f))
        for f in ['gradient.png', 'gradient.webp', 'default.png', 'default.webp']
    )

    if has_gradient:
        print(f"✅ فایل پس‌زمینه پیش‌فرض موجود است")
    else:
        print(f"ℹ️  فایل پس‌زمینه پیش‌فرض وجود ندارد (ربات خودکار ایجاد می‌کند)")
        print(f"   برای ساخت دستی: python3 create_gradient.py")

    return True

def main():
    print("🔍 بررسی تنظیمات ربات...\n")

    checks = [
        ("Python", check_python()),
        ("FFmpeg", check_ffmpeg()),
        ("محیط (.env)", check_env()),
        ("کتابخانه‌ها", check_libraries()),
        ("فونت‌ها", check_fonts()),
        ("Templates", check_templates())
    ]

    print("\n" + "="*50)
    print("📊 خلاصه نتایج:")
    print("="*50)

    all_critical_ok = True
    for name, status in checks:
        if status:
            print(f"✅ {name}")
        else:
            # FFmpeg و Templates اختیاری هستند
            if name not in ["FFmpeg", "Templates", "فونت‌ها"]:
                all_critical_ok = False
            status_icon = "⚠️ " if name in ["FFmpeg", "Templates", "فونت‌ها"] else "❌"
            print(f"{status_icon} {name}")

    print("="*50)

    if all_critical_ok:
        print("\n🎉 همه چیز آماده است! می‌توانید ربات را اجرا کنید:")
        print("   python3 bot.py")
        print("   یا: ./start.sh")
    else:
        print("\n❌ لطفاً مشکلات بالا را برطرف کنید و دوباره تست کنید.")
        sys.exit(1)

if __name__ == "__main__":
    main()
