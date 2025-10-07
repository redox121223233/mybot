# 🚀 راهنمای شروع سریع

این راهنما برای اجرای سریع ربات در کمتر از ۵ دقیقه است!

## قدم 1: پیش‌نیازها (۱ دقیقه)

```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip ffmpeg

# CentOS/RHEL
sudo yum install -y python3 python3-pip ffmpeg
```

## قدم 2: نصب کتابخانه‌ها (۱ دقیقه)

```bash
pip3 install -r requirements.txt
```

## قدم 3: تنظیم توکن (۳۰ ثانیه)

1. از [@BotFather](https://t.me/botfather) توکن ربات بگیرید
2. فایل `.env` بسازید:

```bash
cp .env.example .env
nano .env
```

3. `BOT_TOKEN` را با توکن واقعی جایگزین کنید

## قدم 4: دانلود فونت‌ها (۲ دقیقه)

```bash
./download_fonts.sh
```

**یا دانلود دستی:**

مراجعه کنید به `fonts/README.md`

## قدم 5: اجرا! (۱۰ ثانیه)

```bash
./start.sh
```

یا:

```bash
python3 bot.py
```

## ✅ تمام!

ربات شما اکنون آماده است. به تلگرام بروید و با ربات خود `/start` بزنید!

---

## 🆘 مشکل دارید؟

### خطا: BOT_TOKEN not set

```bash
# مطمئن شوید فایل .env دارید و BOT_TOKEN در آن هست
cat .env
```

### خطا: No module named 'aiogram'

```bash
# کتابخانه‌ها را نصب کنید
pip3 install -r requirements.txt
```

### خطا: Font not found

```bash
# فونت‌ها را دانلود کنید
./download_fonts.sh

# یا به صورت دستی از fonts/README.md
```

### ربات ریستارت می‌شود

```bash
# تست تنظیمات
python3 test_setup.py

# مشاهده خطاها
python3 bot.py
```

---

## 📚 اطلاعات بیشتر

- راهنمای کامل: `README.md`
- راهنمای نصب: `INSTALL.md`
- راهنمای مدیریت: `MANAGE.md`
