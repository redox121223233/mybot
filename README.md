# Telegram Sticker Bot

یک ربات تلگرام برای ساخت استیکرهای سفارشی با قابلیت‌های پیشرفته

## ویژگی‌ها

- ساخت استیکر ساده با تنظیمات سریع
- ساخت استیکر پیشرفته با تنظیمات کامل
- مدیریت پک‌های استیکر
- پشتیبانی از متن فارسی و انگلیسی
- فونت‌های متنوع
- محدودیت استفاده روزانه
- پنل ادمین

## ساختار پروژه

```
mybot/
├── api/
│   ├── __init__.py
│   └── index.py          # Vercel serverless function
├── bot_core/
│   ├── __init__.py
│   ├── config.py         # Configuration settings
│   ├── bot_logic.py      # Core bot logic and utilities
│   ├── handlers.py       # Message and callback handlers
│   └── start_handler.py  # Start command handler
├── bot.py                # Legacy bot file
├── main.py               # Local development entry point
├── requirements.txt      # Python dependencies
├── vercel.json          # Vercel configuration
└── README.md            # This file
```

## نصب و راه‌اندازی

### برای اجرای محلی

1. نصب وابستگی‌ها:
```bash
pip install -r requirements.txt
```

2. تنظیم متغیر محیطی `BOT_TOKEN`:
```bash
export BOT_TOKEN="your_bot_token_here"
```

3. اجرای ربات:
```bash
python main.py
```

### برای استقرار روی Vercel

1. پروژه را روی Vercel مستقر کنید:
```bash
vercel --prod
```

2. متغیر محیطی `BOT_TOKEN` را در Vercel تنظیم کنید

## متغیرهای محیطی

- `BOT_TOKEN`: توکن ربات تلگرام (ضروری)
- `VERCEL_URL`: آدرس URL برای Vercel (خودکار تنظیم می‌شود)

## قابلیت‌های ادمین

- ارسال پیام همگانی
- ارسال پیام به کاربر خاص
- تغییر سهمیه کاربران

آیدی ادمین: `6053579919`

## کانال مورد نیاز

کاربران باید عضو کانال `@redoxbot_sticker` باشند تا از ربات استفاده کنند.

## پشتیبانی

برای پشتیبانی با `@onedaytoalive` تماس بگیرید.