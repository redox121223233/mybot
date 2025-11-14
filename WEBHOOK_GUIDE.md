# 🤖 راهنمای تنظیم Webhook ربات تلگرام

## 📋 مراحل تنظیم Webhook

### 1. 🔑 دریافت توکن ربات
- به ربات [@BotFather](https://t.me/BotFather) بروید
- دستور `/newbot` را ارسال کنید
- نام و نام کاربری ربات را وارد کنید
- توکن ربات را دریافت کنید (مثلا: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. 🌐 دیپلوی ربات در Vercel
- کد ربات را در GitHub قرار دهید
- در Vercel پروژه جدید بسازید
- متغیرهای محیطی را تنظیم کنید:
  - `BOT_TOKEN`: توکن ربات تلگرام
  - `VERCEL_URL`: آدرس پروژه Vercel

### 3. 🔧 تنظیم Webhook

#### روش اول: استفاده از ابزار HTML
1. فایل `webhook_tool.html` را در مرورگر باز کنید
2. توکن ربات را وارد کنید
3. آدرس Vercel را وارد کنید (مثال: `https://mybot123.vercel.app/api/webhook`)
4. روی "تنظیم Webhook" کلیک کنید

#### روش دوم: استفاده از Python
```bash
python webhook_setter.py
```
سپس توکن و آدرس webhook را وارد کنید.

#### روش سوم: دستی در مرورگر
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_WEBHOOK_URL>
```

مثال:
```
https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook?url=https://mybot123.vercel.app/api/webhook
```

### 4. ✅ تست Webhook

#### تست با ابزار
```bash
python test_webhook.py
```

#### تست دستی
به ربات خود پیام `/test` ارسال کنید. اگر پاسخ داد، webhook درست کار می‌کند.

#### بررسی وضعیت Webhook
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

## 🔧 عیب‌یابی مشکلات رایج

### ❌ خطا: Bad Request: webhook url is invalid
**علت:** آدرس webhook نادرست است
**حل:** مطمئن شوید آدرس با `https://` شروع شود و در دسترس باشد

### ❌ خطا: Bad Request: failed to get webhook url from response
**علت:** سرور webhook در دسترس نیست
**حل:** مطمئن شوید اپلیکیشن شما در Vercel در حال اجراست

### ❌ خطا: Bad Request: can't parse response text
**علت:** سرور به درخواست POST پاسخ درستی نمی‌دهد
**حل:** چک کنید که endpoint `/api/webhook` به درخواست‌های POST پاسخ دهد

### ❌ ربات پیام‌ها را دریافت نمی‌کند
**علت:** webhook تنظیم نشده یا غلط تنظیم شده
**حل:** دوباره مراحل بالا را انجام دهید

## 📞 مثال عملی

فرض کنیم:
- توکن ربات: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
- آدرس Vercel: `https://my-sticker-bot.vercel.app`

آدرس کامل تنظیم webhook:
```
https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook?url=https://my-sticker-bot.vercel.app/api/webhook
```

این آدرس را در مرورگر باز کنید. اگر پیام موفقیت‌آمیز دریافت کردید، ربات شما آماده است!

## ✅ بررسی نهایی

پس از تنظیم webhook، موارد زیر را چک کنید:

1. ✅ پیام `{"ok":true,"result":true,"description":"Webhook was set"}` دریافت شد
2. ✅ با فرستادن `/test` به ربات، پاسخی دریافت می‌کنید
3. ✅ دستورات اصلی ربات (`/start`, `/help`) کار می‌کنند
4. ✅ دکمه‌های ربات پاسخ می‌دهند

اگر تمام موارد بالا درست بود، ربات شما آماده استفاده است! 🎉

---

**🔗 لینک‌های مفید:**
- [BotFather](https://t.me/BotFather)
- [API Documentation](https://core.telegram.org/bots/api)
- [Vercel Dashboard](https://vercel.com/dashboard)