# 🎉 خلاصه پروژه - ربات استیکر ساز تلگرام

## ✅ آماده شده در برنچ bot1

تمام فایلهای لازم برای اجرای ربات استیکر ساز تلگرام آماده شده است.

---

## 📦 فایلهای ایجاد شده

### 🎯 فایلهای اصلی (2 فایل)
- ✅ `bot.py` - فایل اصلی ربات (59KB)
- ✅ `requirements.txt` - کتابخانه‌های پایتون

### 🚀 اسکریپت‌های کمکی (5 فایل)
- ✅ `start.sh` - راه‌انداز خودکار ربات
- ✅ `download_fonts.sh` - دانلود خودکار فونت‌ها
- ✅ `test_setup.py` - تست تنظیمات قبل از اجرا
- ✅ `create_gradient.py` - ساخت پس‌زمینه پیش‌فرض
- ✅ `telegram-bot.service` - فایل systemd برای اجرا در پس‌زمینه

### 📚 مستندات (5 فایل)
- ✅ `README.md` - راهنمای کامل پروژه
- ✅ `QUICKSTART.md` - راهنمای شروع سریع (۵ دقیقه)
- ✅ `INSTALL.md` - راهنمای نصب در سیستم‌عامل‌های مختلف
- ✅ `MANAGE.md` - راهنمای مدیریت و نگهداری
- ✅ `PROJECT_SETUP.md` - توضیح کامل فایلهای پروژه

### ⚙️ تنظیمات (3 فایل)
- ✅ `.env` - فایل تنظیمات محیطی (موجود)
- ✅ `.env.example` - نمونه فایل .env
- ✅ `.gitignore` - فایلهای نادیده گرفته شده

### 📁 پوشه‌ها (2 پوشه)
- ✅ `fonts/` - پوشه فونت‌ها + راهنمای دانلود
- ✅ `templates/` - پوشه قالب‌ها + راهنما

---

## 🎯 چه کارهایی باید انجام بدید؟

### 1️⃣ نصب پیش‌نیازها
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip ffmpeg

# CentOS/RHEL
sudo yum install python3 python3-pip ffmpeg
```

### 2️⃣ نصب کتابخانه‌ها
```bash
pip3 install -r requirements.txt
```

### 3️⃣ تنظیم توکن ربات
```bash
# فایل .env را ویرایش کنید
nano .env

# BOT_TOKEN را با توکن واقعی خود جایگزین کنید
```

### 4️⃣ دانلود فونت‌ها
```bash
# روش خودکار
./download_fonts.sh

# یا روش دستی: fonts/README.md را مطالعه کنید
```

### 5️⃣ تست و اجرا
```bash
# تست تنظیمات
python3 test_setup.py

# اجرای ربات
./start.sh

# یا
python3 bot.py
```

---

## 📋 فونت‌های مورد نیاز

شما باید این فونت‌ها را دانلود کنید و در پوشه `fonts/` قرار دهید:

1. **Vazirmatn** (وزیرمتن)
   - https://github.com/rastikerdar/vazirmatn/releases
   - فایل‌ها: `Vazirmatn-Regular.ttf`, `Vazirmatn-Medium.ttf`

2. **Noto Naskh Arabic** (نوتو نسخ عربی)
   - https://fonts.google.com/noto/specimen/Noto+Naskh+Arabic
   - فایل‌ها: `NotoNaskhArabic-Regular.ttf`, `NotoNaskhArabic-Medium.ttf`

3. **Sahel** (ساحل)
   - https://github.com/rastikerdar/sahel-font/releases
   - فایل‌ها: `Sahel.ttf`, `Sahel-Bold.ttf`

4. **IRANSans** (ایران سنس)
   - https://github.com/rastikerdar/iran-sans/releases
   - فایل‌ها: `IRANSans.ttf`, `IRANSansX-Regular.ttf`

⚡ **نکته:** اسکریپت `download_fonts.sh` اکثر فونت‌ها را خودکار دانلود می‌کند!

---

## 🎁 امکانات ربات

### برای کاربران:
- ✅ ساخت استیکر تصویری با متن فارسی
- ✅ ساخت استیکر ویدیویی با متن فارسی
- ✅ انتخاب فونت، رنگ، اندازه و موقعیت متن
- ✅ پس‌زمینه شفاف، پیش‌فرض یا سفارشی
- ✅ ساخت و مدیریت پک استیکر شخصی
- ✅ عضویت اجباری در کانال
- ✅ سهمیه روزانه ۵ استیکر هوشمند

### برای ادمین:
- ✅ مشاهده آمار کاربران
- ✅ مشاهده نتایج نظرسنجی
- ✅ ریست سهمیه کاربران
- ✅ ارسال پیام به کاربران
- ✅ حالت نگهداری
- ✅ سهمیه نامحدود

---

## 🚀 روشهای اجرا

### روش 1: اجرای ساده
```bash
python3 bot.py
```

### روش 2: اجرا در پس‌زمینه (nohup)
```bash
nohup python3 bot.py > bot.log 2>&1 &
```

### روش 3: استفاده از systemd (پیشنهادی)
```bash
sudo cp telegram-bot.service /etc/systemd/system/
sudo nano /etc/systemd/system/telegram-bot.service  # تنظیم User و WorkingDirectory
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

### روش 4: استفاده از screen
```bash
screen -S telegram-bot
python3 bot.py
# Ctrl+A سپس D برای جدا شدن
```

---

## 📊 ساختار نهایی

```
project/
├── bot.py                      ← فایل اصلی ربات
├── requirements.txt            ← کتابخانه‌های Python
│
├── start.sh                    ← راه‌انداز سریع
├── download_fonts.sh           ← دانلود فونت‌ها
├── test_setup.py               ← تست تنظیمات
├── create_gradient.py          ← ساخت پس‌زمینه
├── telegram-bot.service        ← فایل systemd
│
├── README.md                   ← راهنمای کامل
├── QUICKSTART.md               ← شروع سریع
├── INSTALL.md                  ← راهنمای نصب
├── MANAGE.md                   ← راهنمای مدیریت
├── PROJECT_SETUP.md            ← توضیح فایلها
│
├── .env                        ← تنظیمات (BOT_TOKEN)
├── .env.example                ← نمونه .env
├── .gitignore                  ← فایلهای ignored
│
├── fonts/                      ← فونت‌های فارسی
│   └── README.md              ← راهنمای دانلود
│
└── templates/                  ← قالب‌های پیش‌فرض
    └── README.md              ← راهنما
```

---

## ⚡ دستورات سریع

```bash
# تست تنظیمات
python3 test_setup.py

# اجرای ربات
./start.sh

# مشاهده لاگ (systemd)
sudo journalctl -u telegram-bot -f

# ریستارت ربات (systemd)
sudo systemctl restart telegram-bot

# توقف ربات (systemd)
sudo systemctl stop telegram-bot

# بررسی وضعیت
sudo systemctl status telegram-bot
```

---

## 📞 پشتیبانی

اگر مشکلی داشتید:

1. **تست کنید:** `python3 test_setup.py`
2. **راهنماها را بخوانید:**
   - `QUICKSTART.md` - شروع سریع
   - `INSTALL.md` - نصب کامل
   - `MANAGE.md` - مدیریت ربات
3. **لاگ‌ها را بررسی کنید**
4. **Issue در GitHub ایجاد کنید**

---

## ✨ نکات مهم

⚠️ **بدون cron job** - ربات با polling کار می‌کند (بدون نیاز به webhook)

⚠️ **فونت‌ها ضروری است** - بدون فونت فارسی، متن درست نمایش نمی‌شود

⚠️ **FFmpeg اختیاری** - فقط برای استیکرهای ویدیویی لازم است

✅ **همه چیز آماده است** - فقط فونت‌ها را دانلود کنید و توکن را تنظیم کنید!

---

## 🎯 خلاصه

✅ تمام فایلهای لازم ساخته شد
✅ مستندات کامل آماده است
✅ اسکریپت‌های کمکی نوشته شد
✅ پروژه آماده اجراست

**فقط باید:**
1. کتابخانه‌ها را نصب کنید
2. توکن ربات را تنظیم کنید
3. فونت‌ها را دانلود کنید
4. ربات را اجرا کنید

---

🚀 **موفق باشید!**
