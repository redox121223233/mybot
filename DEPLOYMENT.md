# 🚀 راهنمای استقرار ربات

## ⚠️ مهم: Vercel پشتیبانی نمی‌شود!

**این ربات روی Vercel کار نمی‌کند** چون:
- ربات ما یک برنامه مستمر (long-running) است
- Vercel فقط برای سرورLESS functions مناسب است
- ربات تلگرام باید همیشه در حال اجرا باشد

## ✅ سرورهای پشتیبانی شده:

### 1. 🚂 Railway (توصیه شده)
```bash
1. به railway.app بروید
2. New Project → Deploy from GitHub repo
3. ریپازیتوری redox121223233/mybot را انتخاب کنید
4. متغیر محیطی BOT_TOKEN را تنظیم کنید
5. Deploy کنید!
```

### 2. 🎨 Render
```bash
1. به render.com بروید
2. New Web Service → Connect GitHub
3. ریپازیتوری را انتخاب کنید
4. Build Command: pip install -r requirements.txt
5. Start Command: python app.py
6. BOT_TOKEN را در Environment Variables تنظیم کنید
```

### 3. 🐳 Docker
```bash
docker build -t sticker-bot .
docker run -e BOT_TOKEN="YOUR_TOKEN" sticker-bot
```

### 4. 🖥️ VPS مستقیم
```bash
git clone https://github.com/redox121223233/mybot.git
cd mybot
pip install -r requirements.txt
export BOT_TOKEN="YOUR_TOKEN"
python app.py
```

## 🔧 متغیرهای محیطی:
- `BOT_TOKEN`: توکن ربات تلگرام (ضروری)
- `ADMIN_ID`: آیدی ادمین (اختیاری: 6053579919)

## 📋 نیازمندی‌ها سرور:
- Python 3.8+
- اینترنت (برای اتصال به تلگرام)
- FFmpeg (برای تبدیل ویدیو - اتوماتیک نصب می‌شود)

## 🚫 چرا Vercel کار نمی‌کند؟
Vercel برای وب‌سایت‌ها و APIهای کوتاه ساخته شده، نه ربات‌های تلگرام که باید 24/7 اجرا شوند.

---
**لطفاً از Railway یا Render استفاده کنید!** 🌟