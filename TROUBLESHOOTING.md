# ربات تلگرامی - راهنمای عیب‌یابی

## مشکلات رایج و راه‌حل‌ها

### ۱. خطای "name 'Dispatcher' is not defined"
**علت:** عدم وارد کردن (import) کلاس Dispatcher در فایل handlers.py
**راه‌حل:** اضافه کردن `Dispatcher` به import‌های aiogram در handlers.py

```python
from aiogram import F, Router, types, Dispatcher
```

### ۲. خطاهای 404 در Vercel
**علت:** تنظیمات نامناسب مسیردهی (routing) در vercel.json
**راه‌حل:** به‌روزرسانی vercel.json با مسیردهی صحیح:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/webhook",
      "dest": "api/index.py"
    },
    {
      "src": "/",
      "dest": "api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

### ۳. خطاهای مربوط به BOT_TOKEN
**علت:** عدم تنظیم متغیر محیطی BOT_TOKEN در Vercel
**راه‌حل:**
1. وارد حساب Vercel خود شوید
2. به پروژه ربات بروید
3. به تب Settings → Environment Variables بروید
4. متغیر BOT_TOKEN را با توکن ربات خود اضافه کنید

### ۴. مشکلات مربوط به Webhook
**علت:** عدم تنظیم صحیح webhook در تلگرام
**راه‌حل:**
1. پس از استقرار در Vercel، URL webhook را دریافت کنید
2. با استفاده از توکن ربات، webhook را تنظیم کنید:

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-vercel-app.vercel.app/webhook"}'
```

### ۵. خطاهای مربوط به وابستگی‌ها (Dependencies)
**علت:** نصب نبودن پکیج‌های مورد نیاز
**راه‌حل:** مطمئن شوید تمام پکیج‌های زیر در requirements.txt وجود دارند:

```
aiogram>=3.4.1,<4.0.0
fastapi
uvicorn[standard]
Pillow
arabic-reshaper
python-bidi
python-multipart
```

## تست محلی
برای تست ربات به صورت محلی:
1. متغیر BOT_TOKEN را تنظیم کنید:
   ```bash
   export BOT_TOKEN="your_bot_token_here"
   ```
2. سرور را اجرا کنید:
   ```bash
   uvicorn api.index:app --host 0.0.0.0 --port 8000
   ```
3. با استفاده از ابزارهایی مانند Postman یا curl تست کنید:
   ```bash
   curl -X POST http://localhost:8000/webhook \
        -H "Content-Type: application/json" \
        -d '{"update_id": 1, "message": {"message_id": 1, "from": {"id": 1}, "chat": {"id": 1}, "text": "/start"}}'
   ```

## لاگ‌گیری و دیباگ
- برای مشاهده لاگ‌ها در Vercel: به تب Functions → Logs بروید
- در محیط توسعه: لاگ‌ها در ترمینال نمایش داده می‌شوند
- برای دیباگ بیشتر، می‌توانید لاگینگ را در DEBUG mode تنظیم کنید:

```python
logging.basicConfig(level=logging.DEBUG)
```

## منابع مفید
- [مستندات aiogram](https://docs.aiogram.dev/)
- [مستندات FastAPI](https://fastapi.tiangolo.com/)
- [مستندات Vercel](https://vercel.com/docs)