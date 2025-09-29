# ربات ساخت استیکر تلگرام

ربات قدرتمند برای ساخت استیکر تصویری با پشتیبانی کامل از فونت فارسی

## ویژگی‌ها

- ✅ ساخت استیکر ساده با متن فارسی و انگلیسی
- ✅ پشتیبانی از فونت‌های فارسی
- ✅ مدیریت پک استیکر شخصی
- ✅ سهمیه روزانه برای کاربران رایگان
- ✅ سازگار با Railway و Vercel
- ✅ رابط کاربری ساده و کاربرپسند

## استقرار روی Vercel (پیشنهادی)

### مرحله 1: آماده‌سازی

1. **کلون کردن پروژه:**
```bash
git clone https://github.com/your-username/telegram-sticker-bot.git
cd telegram-sticker-bot
```

2. **نصب وابستگی‌ها (برای تست محلی):**
```bash
pip install -r requirements.txt
```

### مرحله 2: تنظیم GitHub

1. Repository جدید در GitHub ایجاد کنید
2. کد را push کنید:
```bash
git add .
git commit -m "Initial commit for Vercel"
git push origin main
```

### مرحله 3: استقرار روی Vercel

1. به [vercel.com](https://vercel.com) بروید
2. با GitHub وارد شوید
3. "New Project" → Repository خود را انتخاب کنید
4. متغیرهای محیطی را تنظیم کنید:

**متغیرهای اجباری:**
- `BOT_TOKEN`: توکن ربات تلگرام
- `WEBHOOK_SECRET`: کلید امنیتی (مثلاً `my_secret_key`)

**متغیرهای اختیاری:**
- `BOT_USERNAME`: نام کاربری ربات (بدون @)
- `CHANNEL_LINK`: کانال اجباری (مثلاً `@YourChannel`)
- `ADMIN_ID`: شناسه عددی ادمین
- `SUPPORT_ID`: پشتیبانی (مثلاً `@support`)

5. "Deploy" کلیک کنید

### مرحله 4: تنظیم Webhook

پس از deploy موفق، URL زیر را در مرورگر باز کنید:

```
https://api.telegram.org/bot[BOT_TOKEN]/setWebhook?url=https://your-project.vercel.app/webhook/[WEBHOOK_SECRET]
```

**مثال:**
```
https://api.telegram.org/bot123456789:ABC.../setWebhook?url=https://my-bot.vercel.app/webhook/my_secret_key
```

### مرحله 5: تست

1. ربات را در تلگرام پیدا کنید
2. `/start` ارسال کنید
3. متنی ارسال کنید تا استیکر بسازد

## استقرار روی Railway (روش قدیمی)

### مرحله 1: نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### مرحله 2: تنظیم متغیرهای محیطی

در پنل Railway، Variables را اضافه کنید:
- `BOT_TOKEN`: توکن ربات تلگرام

### مرحله 3: Deploy

1. فایل‌ها را به GitHub push کنید
2. Railway را به repository متصل کنید
3. Deploy خودکار انجام می‌شود

## ساختار پروژه

```
├── api/                    # API endpoints برای Vercel
│   ├── index.py           # صفحه اصلی
│   ├── webhook.py         # پردازش پیام‌های تلگرام
│   └── health.py          # بررسی سلامت
├── bot.py                 # فایل اصلی ربات (برای Railway)
├── requirements.txt       # وابستگی‌های Python
├── vercel.json           # تنظیمات Vercel
├── Dockerfile            # برای Railway/Docker
├── setup_vercel.py       # اسکریپت راه‌اندازی
├── VERCEL_DEPLOYMENT.md  # راهنمای کامل Vercel
└── README.md             # این فایل
```

## تنظیمات

### متغیرهای محیطی

| متغیر | اجباری | توضیح | مثال |
|-------|---------|-------|-------|
| `BOT_TOKEN` | ✅ | توکن ربات تلگرام | `123456789:ABC...` |
| `WEBHOOK_SECRET` | ✅ | کلید امنیتی webhook | `my_secret_key` |
| `BOT_USERNAME` | ❌ | نام کاربری ربات | `MyBot` |
| `CHANNEL_LINK` | ❌ | کانال اجباری | `@MyChannel` |
| `ADMIN_ID` | ❌ | شناسه ادمین | `123456789` |
| `SUPPORT_ID` | ❌ | پشتیبانی | `@support` |

### محدودیت‌ها

- **کاربران رایگان:** 5 استیکر در روز
- **کاربران اشتراکی:** نامحدود
- **حداکثر طول متن:** 100 کاراکتر
- **فرمت‌های پشتیبانی شده:** متن فارسی و انگلیسی

## استفاده

### دستورات اصلی

- `/start` - شروع ربات
- `/help` - راهنمای استفاده

### ساخت استیکر

1. ربات را استارت کنید
2. متن دلخواه خود را ارسال کنید
3. استیکر خودکار ساخته و ارسال می‌شود

## مشکلات رایج

### ربات پاسخ نمی‌دهد
- بررسی کنید webhook درست تنظیم شده
- متغیرهای محیطی را چک کنید
- لاگ‌های Vercel را بررسی کنید

### خطای 500
- `BOT_TOKEN` را بررسی کنید
- `WEBHOOK_SECRET` را چک کنید
- از طریق `/api/health` سلامت سیستم را بررسی کنید

### استیکر ساخته نمی‌شود
- متن را کوتاه‌تر کنید
- از کاراکترهای خاص اجتناب کنید
- محدودیت روزانه را بررسی کنید

## ابزارهای کمکی

### اسکریپت راه‌اندازی
```bash
python setup_vercel.py
```

### بررسی سلامت
```
https://your-project.vercel.app/api/health
```

### مشاهده وضعیت webhook
```
https://api.telegram.org/bot[BOT_TOKEN]/getWebhookInfo
```

## مقایسه پلتفرم‌ها

| ویژگی | Vercel | Railway |
|--------|--------|---------|
| رایگان | ✅ | ✅ |
| راه‌اندازی | آسان | متوسط |
| عملکرد | عالی | خوب |
| محدودیت زمان | 10 ثانیه | نامحدود |
| پشتیبانی فایل | محدود | کامل |
| مناسب برای | ربات‌های ساده | ربات‌های پیچیده |

## توسعه

### اضافه کردن قابلیت جدید

1. فایل جدید در `api/` ایجاد کنید
2. تابع `handler(event, context)` تعریف کنید
3. در `vercel.json` route اضافه کنید

### تست محلی

```bash
# نصب Vercel CLI
npm i -g vercel

# اجرای محلی
vercel dev
```

## مشارکت

1. Fork کنید
2. Branch جدید ایجاد کنید
3. تغییرات را commit کنید
4. Pull Request ارسال کنید

## لایسنس

این پروژه تحت لایسنس MIT منتشر شده است.

## پشتیبانی

- 📖 [راهنمای کامل Vercel](VERCEL_DEPLOYMENT.md)
- 🐛 [گزارش مشکل](https://github.com/your-repo/issues)
- 💬 [بحث و گفتگو](https://github.com/your-repo/discussions)

---

**✨ ساخته شده با عشق برای جامعه توسعه‌دهندگان ایرانی**
