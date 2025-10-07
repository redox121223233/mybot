# 📦 فایلهای پروژه ربات استیکر ساز

این سند توضیح می‌دهد که چه فایل‌هایی در پروژه وجود دارد و هر کدام چه کاری انجام می‌دهند.

## 🎯 فایلهای اصلی

### `bot.py`
**فایل اصلی ربات** - تمام منطق ربات در این فایل است:
- مدیریت استیکرهای ساده و هوشمند
- پشتیبانی از استیکرهای تصویری و ویدیویی
- مدیریت پک استیکر
- پنل ادمین
- سیستم سهمیه روزانه

### `requirements.txt`
**لیست کتابخانه‌های پایتون** مورد نیاز:
- `aiogram` - کتابخانه ربات تلگرام
- `Pillow` - پردازش تصویر
- `arabic-reshaper` - پشتیبانی از متن فارسی
- `python-bidi` - راست‌چین کردن متن فارسی

## 🚀 فایلهای راه‌اندازی

### `start.sh`
**اسکریپت راه‌انداز اصلی** - اجرای ربات با چک کردن همه چیز:
```bash
./start.sh
```

### `test_setup.py`
**تست تنظیمات قبل از اجرا** - بررسی:
- نسخه Python
- نصب FFmpeg
- وجود فایل .env
- نصب کتابخانه‌ها
- وجود فونت‌ها

```bash
python3 test_setup.py
```

### `create_gradient.py`
**ساخت تصویر پیش‌فرض** - یک گرادیانت زیبا برای پس‌زمینه:
```bash
python3 create_gradient.py
```

### `download_fonts.sh`
**دانلود خودکار فونت‌ها** - دانلود فونت‌های فارسی:
```bash
./download_fonts.sh
```

## 📝 فایلهای مستندات

### `README.md`
راهنمای کامل پروژه - شامل:
- معرفی پروژه
- نیازمندی‌ها
- نصب و راه‌اندازی
- امکانات

### `QUICKSTART.md`
راهنمای شروع سریع - برای اجرا در ۵ دقیقه

### `INSTALL.md`
راهنمای نصب کامل - نصب در سیستم‌عامل‌های مختلف:
- Ubuntu/Debian
- CentOS/RHEL
- Windows

### `MANAGE.md`
راهنمای مدیریت ربات - شامل:
- کنترل ربات (start/stop/restart)
- مانیتورینگ و لاگ‌ها
- عیب‌یابی
- بک‌آپ و بروزرسانی
- بهینه‌سازی

### `PROJECT_SETUP.md` (همین فایل)
توضیح فایلهای پروژه

## ⚙️ فایلهای تنظیمات

### `.env`
**تنظیمات محیطی** - حاوی توکن ربات:
```env
BOT_TOKEN=your_token_here
```

### `.env.example`
**نمونه فایل .env** - برای کپی و تنظیم:
```bash
cp .env.example .env
```

### `.gitignore`
**فایلهای نادیده گرفته شده در Git** - شامل:
- `.env` (برای امنیت)
- فایلهای فونت
- فایلهای لاگ
- داده‌های کاربران

### `telegram-bot.service`
**فایل systemd** - برای اجرای ربات به صورت سرویس:
```bash
sudo cp telegram-bot.service /etc/systemd/system/
sudo systemctl start telegram-bot
```

## 📁 پوشه‌ها

### `fonts/`
**پوشه فونت‌های فارسی** - باید شامل فونت‌های زیر باشد:
- Vazirmatn (وزیرمتن)
- Noto Naskh Arabic (نوتو نسخ عربی)
- Sahel (ساحل)
- IRANSans (ایران سنس)

📖 راهنما: `fonts/README.md`

### `templates/`
**پوشه قالب‌های پیش‌فرض** - تصاویر پس‌زمینه:
- `gradient.png` (اختیاری - ربات خودکار می‌سازد)

📖 راهنما: `templates/README.md`

## 🔧 ساختار نهایی پروژه

```
project/
├── bot.py                    # فایل اصلی ربات
├── requirements.txt          # کتابخانه‌های Python
├── .env                      # تنظیمات محیطی (شما باید بسازید)
├── .env.example             # نمونه فایل .env
├── .gitignore               # فایلهای نادیده گرفته شده
│
├── start.sh                 # اسکریپت راه‌انداز
├── test_setup.py            # تست تنظیمات
├── create_gradient.py       # ساخت پس‌زمینه پیش‌فرض
├── download_fonts.sh        # دانلود فونت‌ها
├── telegram-bot.service     # فایل systemd
│
├── README.md                # راهنمای اصلی
├── QUICKSTART.md            # راهنمای سریع
├── INSTALL.md               # راهنمای نصب
├── MANAGE.md                # راهنمای مدیریت
├── PROJECT_SETUP.md         # این فایل
│
├── fonts/                   # پوشه فونت‌ها
│   ├── README.md           # راهنمای دانلود فونت
│   ├── Vazirmatn-Regular.ttf    (شما باید دانلود کنید)
│   ├── Vazirmatn-Medium.ttf     (شما باید دانلود کنید)
│   ├── NotoNaskhArabic-*.ttf    (شما باید دانلود کنید)
│   ├── Sahel*.ttf               (شما باید دانلود کنید)
│   └── IRANSans*.ttf            (شما باید دانلود کنید)
│
└── templates/               # پوشه قالب‌ها
    ├── README.md           # راهنمای قالب‌ها
    └── gradient.png        (اختیاری - خودکار ساخته می‌شود)
```

## ✅ چک‌لیست راه‌اندازی

قبل از اجرای ربات، مطمئن شوید:

- [ ] Python 3.9+ نصب شده
- [ ] FFmpeg نصب شده (برای استیکر ویدیویی)
- [ ] کتابخانه‌های Python نصب شده (`pip install -r requirements.txt`)
- [ ] فایل `.env` وجود دارد و `BOT_TOKEN` در آن تنظیم شده
- [ ] فونت‌های فارسی در پوشه `fonts/` دانلود شده
- [ ] اسکریپت‌ها executable هستند (`chmod +x *.sh`)

برای تست سریع:
```bash
python3 test_setup.py
```

## 🚀 اجرای سریع

```bash
# نصب پیش‌نیازها
sudo apt install python3 python3-pip ffmpeg

# نصب کتابخانه‌ها
pip3 install -r requirements.txt

# تنظیم توکن
cp .env.example .env
nano .env  # BOT_TOKEN را وارد کنید

# دانلود فونت‌ها
./download_fonts.sh

# اجرا
./start.sh
```

## 📞 پشتیبانی

در صورت مشکل:
1. `python3 test_setup.py` را اجرا کنید
2. `README.md` را مطالعه کنید
3. `INSTALL.md` را بررسی کنید
4. Issue در GitHub ایجاد کنید
