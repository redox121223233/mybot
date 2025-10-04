# راهنمای Webhook ربات تلگرام

## ✅ وضعیت فعلی

- ✅ **Webhook تنظیم شده**: ربات با موفقیت به آدرس `https://mybot-zx31.vercel.app` متصل شده
- ✅ **Token معتبر**: BOT_TOKEN به درستی تنظیم شده
- ✅ **Push به GitHub**: تمام تغییرات به repository ارسال شده
- ⚠️ **Vercel deployment**: نیاز به بررسی دارد (خطای 500)

## 📋 فایل‌های ایجاد شده

### 1. `vercel.json`
```json
{
  "version": 2,
  "functions": {
    "api/index.py": {
      "runtime": "python3.9",
      "maxDuration": 30
    }
  },
  "env": {
    "BOT_TOKEN": "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0",
    "WEBHOOK_URL": "https://mybot-zx31.vercel.app"
  },
  "routes": [
    {
      "src": "/webhook",
      "dest": "api/index.py"
    },
    {
      "src": "/health",
      "dest": "api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

### 2. `api/index.py`
فایل handler برای Vercel که:
- پیام‌های webhook را دریافت می‌کند
- Updateها را پردازش می‌کند
- Health check پاسخ می‌دهد

### 3. `setup_webhook.py`
اسکریپت تنظیم webhook:
```bash
python setup_webhook.py
```

### 4. `test_webhook.py`
اسکریپت تست webhook:
```bash
python test_webhook.py
```

### 5. `delete_webhook.py`
اسکریپت حذف webhook (در صورت نیاز):
```bash
python delete_webhook.py
```

## 🔧 دستورات مهم

### تنظیم webhook
```bash
cd mybot
python setup_webhook.py
```

### تست webhook
```bash
python test_webhook.py
```

### حذف webhook
```bash
python delete_webhook.py
```

## 📊 نتایج تست

### ✅ موفق
- Webhook تنظیم شده: `https://mybot-zx31.vercel.app`
- هیچ خطایی در Telegram ثبت نشده
- BOT_TOKEN معتبر است

### ⚠️ نیاز به بررسی
- Vercel deployment خطای 500 می‌دهد
- ممکن است نیاز به rebuild در Vercel داشته باشیم

## 🚀 مراحل بعدی

1. **بررسی Vercel Dashboard** - برای دیدن لاگ‌های خطا
2. **Rebuild دستی** - در صورت نیاز rebuild در Vercel
3. **تست نهایی** - ارسال پیام به ربات برای تست کامل

## 📞 پشتیبانی

در صورت بروز مشکل:
- از اسکریپت `test_webhook.py` استفاده کنید
- خروجی را بررسی کنید
- در صورت نیاز webhook را دوباره تنظیم کنید