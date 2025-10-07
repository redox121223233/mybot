# 🚀 راهنمای تنظیم Vercel Deployment

## 📋 مراحل تنظیم

### 1. نصب Vercel CLI (اختیاری)
```bash
npm i -g vercel
```

### 2. Deployment در Vercel

#### روش 1: از GitHub
1. به [vercel.com](https://vercel.com) بروید
2. Import پروژه از GitHub
3. انتخاب برنچ `bot1`
4. تنظیمات:
   - **Framework**: Python
   - **Root Directory**: `.`

#### روش 2: از CLI
```bash
cd mybot
vercel --prod
```

### 3. تنظیم Environment Variables

#### در Vercel Dashboard:
1. به پروژه بروید
2. Settings → Environment Variables
3. اضافه کردن متغیرها:

| Variable Name | Value |
|---------------|--------|
| `BOT_TOKEN` | `8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0` |
| `WEBHOOK_URL` | `https://your-project-name.vercel.app/webhook` |

#### از CLI:
```bash
# نصب Vercel CLI
npm i -g vercel

# تنظیم متغیرها
vercel env add BOT_TOKEN production
# وارد کنید: 8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0

vercel env add WEBHOOK_URL production  
# وارد کنید: https://your-project-name.vercel.app/webhook
```

### 4. تنظیم Webhook

پس از deployment موفق، webhook را تنظیم کنید:

```bash
cd mybot
python setup_vercel_webhook.py
```

### 5. تست نهایی

```bash
# تست webhook
curl -X POST https://your-project-name.vercel.app/webhook \
  -H "Content-Type: application/json" \
  -d '{"update_id": 123, "message": {"text": "/start", "chat": {"id": 123}}}'

# تست health
curl https://your-project-name.vercel.app/health
```

## 🔧 مشکلات احتمالی و راه‌حل

### 1. خطای Environment Variables
- **علت**: استفاده از @bot_token که نیاز به Secret دارد
- **راه‌حل**: استفاده از متغیر مستقیم یا تنظیم Secret در Vercel

### 2. خطای Import
- **علت**: مسیر import اشتباه
- **راه‌حل**: استفاده از sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

### 3. خطای Async
- **علت**: Vercel با asyncio مشکل دارد
- **راه‌حل**: استفاده از asyncio.run() در handler

## 📊 ساختار فایل‌های نهایی

```
mybot/
├── api/
│   ├── __init__.py
│   ├── index.py          # handler اصلی
│   ├── webhook.py        # handler webhook
│   └── bot_functions.py  # توابع مشترک
├── vercel.json          # تنظیمات Vercel بدون خطا
├── requirements.txt     # وابستگی‌ها
├── setup_vercel_webhook.py
├── bot.py              # کد اصلی ربات
└── ...
```

## ✅ چک‌لیست نهایی

- [ ] پروژه در Vercel deploy شده
- [ ] Environment Variables تنظیم شده
- [ ] Webhook تنظیم شده
- [ ] تست با ارسال پیام انجام شده
- [ ] لاگ‌ها بررسی شده

## 📞 پشتیبانی

در صورت مشکل:
1. لاگ‌های Vercel را بررسی کنید
2. Environment Variables را دوباره بررسی کنید
3. از اسکریپت تست استفاده کنید