# راهنمای نصب سریع ربات استیکر ساز

## 🚀 نصب سریع (Ubuntu/Debian)

```bash
# 1. نصب پیش‌نیازها
sudo apt update
sudo apt install -y python3 python3-pip ffmpeg git

# 2. کلون پروژه (یا دانلود)
git clone <repository-url>
cd project

# 3. نصب کتابخانه‌های Python
pip3 install -r requirements.txt

# 4. تنظیم توکن ربات
# فایل .env را ویرایش کرده و BOT_TOKEN را وارد کنید
nano .env

# 5. دانلود فونت‌های فارسی
# راهنمای کامل در fonts/README.md
# یا از این دستور استفاده کنید:
./download_fonts.sh  # (در صورت وجود)

# 6. اجرای ربات
chmod +x start.sh
./start.sh
```

## 🐧 نصب سریع (CentOS/RHEL)

```bash
# 1. نصب پیش‌نیازها
sudo yum install -y python3 python3-pip ffmpeg git

# 2-6: مشابه Ubuntu
```

## 🪟 نصب در Windows

1. Python را از https://python.org دانلود و نصب کنید
2. FFmpeg را از https://ffmpeg.org دانلود و نصب کنید
3. فایل پروژه را دانلود کنید
4. Command Prompt یا PowerShell را باز کنید:

```cmd
cd path\to\project
pip install -r requirements.txt
python create_gradient.py
python bot.py
```

## 📦 فونت‌های فارسی (ضروری)

### دانلود خودکار (Linux):

```bash
# ساخت اسکریپت دانلود فونت
cat > download_fonts.sh << 'EOF'
#!/bin/bash
mkdir -p fonts
cd fonts

# Vazirmatn
wget https://github.com/rastikerdar/vazirmatn/releases/download/v33.003/vazirmatn-v33.003.zip
unzip vazirmatn-v33.003.zip "Vazirmatn*.ttf" && rm vazirmatn-v33.003.zip

# Noto Naskh Arabic (نیاز به دانلود دستی از Google Fonts)
echo "⚠️  Noto Naskh Arabic را از Google Fonts دانلود کنید:"
echo "https://fonts.google.com/noto/specimen/Noto+Naskh+Arabic"

# Sahel
wget https://github.com/rastikerdar/sahel-font/releases/download/v3.4.0/sahel-font-v3.4.0.zip
unzip sahel-font-v3.4.0.zip "Sahel*.ttf" && rm sahel-font-v3.4.0.zip

# IRANSans
wget https://github.com/rastikerdar/iran-sans/releases/download/v5.0/iran-sans-v5.0.zip
unzip iran-sans-v5.0.zip "IRANSans*.ttf" && rm iran-sans-v5.0.zip

echo "✅ فونت‌ها دانلود شدند"
EOF

chmod +x download_fonts.sh
./download_fonts.sh
```

### دانلود دستی:

مراجعه کنید به: `fonts/README.md`

## 🔧 تنظیمات

### فایل .env

```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
```

## 🎯 اجرا

### روش 1: اجرای ساده

```bash
python3 bot.py
```

### روش 2: اجرا در پس‌زمینه

```bash
nohup python3 bot.py > bot.log 2>&1 &
```

### روش 3: استفاده از systemd (پیشنهادی)

```bash
# 1. کپی فایل service
sudo cp telegram-bot.service /etc/systemd/system/

# 2. ویرایش فایل service
sudo nano /etc/systemd/system/telegram-bot.service
# تغییر دهید:
#   - YOUR_USERNAME -> نام کاربری خود
#   - /path/to/project -> مسیر پروژه

# 3. فعال‌سازی و اجرا
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot

# 4. بررسی وضعیت
sudo systemctl status telegram-bot

# 5. مشاهده لاگ‌ها
sudo journalctl -u telegram-bot -f
```

## 🛠 عیب‌یابی

### خطا: FFmpeg not found

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg
```

### خطا: Font not found

فونت‌های فارسی را از `fonts/README.md` دانلود کنید

### خطا: BOT_TOKEN not set

فایل `.env` را ویرایش کرده و توکن ربات را وارد کنید

## 📞 پشتیبانی

در صورت مشکل، Issue در GitHub ایجاد کنید یا با پشتیبانی تماس بگیرید.
