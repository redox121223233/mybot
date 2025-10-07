#!/bin/bash

# اسکریپت راه‌انداز ربات استیکر ساز

echo "🚀 در حال راه‌اندازی ربات استیکر ساز..."

# بررسی نصب Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 نصب نیست. لطفاً ابتدا Python را نصب کنید."
    exit 1
fi

# بررسی نصب FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  هشدار: FFmpeg نصب نیست. استیکرهای ویدیویی کار نخواهند کرد."
    echo "برای نصب FFmpeg:"
    echo "  Ubuntu/Debian: sudo apt install ffmpeg"
    echo "  CentOS/RHEL: sudo yum install ffmpeg"
fi

# بررسی وجود فایل .env
if [ ! -f .env ]; then
    echo "❌ فایل .env وجود ندارد. لطفاً ابتدا BOT_TOKEN را در فایل .env تنظیم کنید."
    exit 1
fi

# بررسی وجود فونت‌ها
if [ ! -d "fonts" ] || [ -z "$(ls -A fonts/*.ttf 2>/dev/null)" ]; then
    echo "⚠️  هشدار: پوشه fonts خالی است. لطفاً فونت‌های فارسی را دانلود کنید."
    echo "راهنما: fonts/README.md را مطالعه کنید."
fi

# بررسی نصب کتابخانه‌ها
echo "📦 بررسی کتابخانه‌های مورد نیاز..."
if ! python3 -c "import aiogram" &> /dev/null; then
    echo "📥 در حال نصب کتابخانه‌ها..."
    pip3 install -r requirements.txt
fi

# ساخت تصویر گرادیانت پیش‌فرض (در صورت نبود)
if [ ! -f "templates/gradient.png" ]; then
    echo "🎨 در حال ساخت تصویر پیش‌فرض..."
    python3 create_gradient.py
fi

echo "✅ همه چیز آماده است!"
echo "🤖 در حال اجرای ربات..."
echo ""

# اجرای ربات
python3 bot.py
