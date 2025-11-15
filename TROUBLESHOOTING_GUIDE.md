# راهنمای عیب‌یابی ربات تلگرامی

## 🚨 مشکل: ربات کار نمی‌کند و لاگ وجود ندارد

### 🔍 مراحل عیب‌یابی

#### مرحله ۱: بررسی URL صحیح
```bash
# ابتدا URL صحیح Vercel خود را پیدا کنید
# مثال: https://my-app.vercel.app
```

#### مرحله ۲: تست endpoint اصلی
```bash
# تست home endpoint
curl https://your-vercel-app.vercel.app/
# باید پاسخ "Enhanced Sticker Bot is running!" را بدهید
```

#### مرحله ۳: تست webhook endpoint
```bash
# تست webhook با داده تست
curl -X POST https://your-vercel-app.vercel.app/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"update_id":123,"message":{"text":"test"}}'
```

#### مرحله ۴: بررسی environment variables
در Vercel Dashboard:
1. وارد پروژه شوید
2. به Settings → Environment Variables بروید
3. مطمئن شوید `BOT_TOKEN` تنظیم شده است
4. مطمئن شوید `VERCEL_URL` به صورت خودکار تنظیم شده است

#### مرحله ۵: استفاده از اسکریپت‌های عیب‌یابی

##### تست webhook:
```python
# فایل debug_webhook.py را اجرا کنید
# ابتدا URL خود را در فایل جایگزین کنید
python debug_webhook.py
```

##### تنظیم webhook:
```python
# فایل set_webhook.py را اجرا کنید
# BOT_TOKEN باید در environment variables باشد
python set_webhook.py
```

### 🔧 راه‌حل‌های احتمالی

#### مشکل ۱: Function ساخته نشده است
**علت:** Vercel فایل `api/index.py` را به عنوان function نشناخته است
**راه‌حل:**
1. مطمئن شوید فایل در مسیر `/api/index.py` قرار دارد
2. از `vercel.json` صحیح استفاده کنید

#### مشکل ۲: BOT_TOKEN تنظیم نشده است
**علت:** Environment variable در Vercel تنظیم نشده
**راه‌حل:**
1. در Vercel Dashboard: Settings → Environment Variables
2. `BOT_TOKEN` را با token ربات خود اضافه کنید
3. redeploy کنید

#### مشکل ۳: Webhook به آدرس اشتباه اشاره می‌کند
**علت:** URL webhook نادرست است
**راه‌حل:**
```bash
# با استفاده از اسکریپت set_webhook.py
python set_webhook.py
# یا به صورت دستی
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-app.vercel.app/api/webhook"
```

#### مشکل ۴: Deploy از برچ اشتباه
**علت:** تغییرات در برچ `fix-vercel-type-error` deploy نشده است
**راه‌حل:**
1. مطمئن شوید از برچ درست deploy می‌کنید
2. یا به main برچ merge کنید

### 📊 بررسی لاگ‌ها در Vercel

#### Method 1: Vercel Dashboard
1. وارد پروژه شوید
2. به تب Functions بروید
3. `/api/webhook` را انتخاب کنید
4. Logs را بررسی کنید

#### Method 2: Vercel CLI
```bash
# نصب Vercel CLI
npm i -g vercel

# لاگ‌های real-time
vercel logs

# لاگ‌های function خاص
vercel logs --filter="/api/webhook"
```

### 🚀 تست نهایی

پس از رفع مشکل:
1. `/start` را به ربات بفرستید
2. بررسی کنید که پاسخ می‌دهد
3. یک عکس تست کنید
4. بررسی کنید که مینی اپ کار می‌کند

### 📞 اگر مشکل ادامه داشت

اطلاعات زیر را ارائه دهید:
- URL دقیق Vercel
- نتیجه تست home endpoint
- نتیجه تست webhook endpoint
- اسکرین‌شات از Vercel Function Logs
- اسکرین‌شات از environment variables

---

## 🔗 اسکریپت‌های مفید

### `debug_webhook.py`
- تست endpoint اصلی و webhook
- نمایش response headers و status codes
- تشخیص مشکلات connectivity

### `set_webhook.py`
- تنظیم مجدد webhook
- حذف webhook قدیمی
- نمایش اطلاعات webhook فعلی

### نحوه استفاده:
1. URL صحیح را در فایل‌ها وارد کنید
2. BOT_TOKEN را در environment variables تنظیم کنید
3. اسکریپت‌ها را اجرا کنید