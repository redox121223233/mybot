# 🐳 راهنمای کامل Docker برای ربات تلگرام

## 📦 Docker Setup کامل

### 1. ساخت Dockerfile کامل

```dockerfile
FROM python:3.11-slim

# نصب FFmpeg و فونت‌ها
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-noto \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# تنظیم دایرکتوری کاری
WORKDIR /app

# کپی فایل‌های requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد ربات
COPY . .

# اجرای ربات
CMD ["python", "bot.py"]
```

### 2. ساخت و اجرای Docker Image

```bash
# ساخت ایمیج
docker build -t telegram-sticker-bot .

# اجرای ربات با فایل env
docker run -d \
  --name sticker-bot \
  --env-file .env \
  -p 8080:8080 \
  telegram-sticker-bot

# یا برای webhook
docker run -d \
  --name sticker-bot \
  --env-file .env \
  -p 8080:8080 \
  telegram-sticker-bot
```

### 3. تست FFmpeg در Docker

```bash
# ورود به کانتینر
docker exec -it sticker-bot bash

# تست FFmpeg
ffmpeg -version

# خروج
exit
```

### 4. لاگ‌گیری از ربات

```bash
# مشاهده لاگ‌ها
docker logs sticker-bot

# دنبال کردن لاگ‌ها به صورت realtime
docker logs -f sticker-bot
```

### 5. مدیریت Docker

```bash
# توقف ربات
docker stop sticker-bot

# شروع مجدد
docker start sticker-bot

# حذف کانتینر
docker rm sticker-bot

# حذف ایمیج
docker rmi telegram-sticker-bot
```

### 6. Docker Compose (اختیاری)

```yaml
version: '3.8'
services:
  sticker-bot:
    build: .
    container_name: telegram-sticker-bot
    env_file: .env
    ports:
      - "8080:8080"
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
```

## ✅ تست نهایی

بعد از اجرا:

1. **تست متن فارسی:**
   ```
   سلام این یک متن فارسی بلند است
   ```

2. **تست استیکر ویدیویی:**
   - ارسال ویدیو کوتاه (زیر 10 ثانیه)
   - یا ارسال GIF

3. **تست محدودیت‌ها:**
   - بیش از 3 استیکر AI در روز
   - بیش از 50 استیکر ساده در روز

## 📋 نکات مهم

### برای سرور VPS:
```bash
# نصب Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# اجرای بدون sudo (اختیاری)
sudo usermod -aG docker $USER
```

### برای امنیت:
- از `.env` برای نگهداری توکن استفاده کنید
- پورت‌ها را محدود کنید
- از SSL/TLS برای webhook استفاده کنید

## 🎯 خلاصه

✅ **Docker بهترین راه حل برای FFmpeg است**
✅ **نیازی به دانلود فایل بزرگ ندارید**
✅ **همه چیز خودکار نصب می‌شود**

## 📞 در صورت مشکل

اگر باز هم خطای FFmpeg داشتید:
1. لاگ Docker را بررسی کنید
2. مطمئن شوید Dockerfile درست است
3. اطلاع دهید تا بررسی کنیم