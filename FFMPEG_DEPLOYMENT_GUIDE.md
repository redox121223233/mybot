# راهنمای استفاده از FFmpeg در ربات

## روش ۱: استفاده از Docker (توصیه‌شده)

### ساخت و اجرای Docker Image:
```bash
# ساخت ایمیج
docker build -t telegram-sticker-bot .

# اجرای ربات
docker run -d --env-file .env telegram-sticker-bot
```

### مزایا:
- ✅ FFmpeg به صورت خودکار نصب می‌شود
- ✅ محیط یکنواخت و قابل پیش‌بینی
- ✅ بدون نیاز به نصب دستی
- ✅ مناسب برای production

## روش ۲: نصب دستی FFmpeg

### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg
```

### CentOS/RHEL:
```bash
sudo yum install ffmpeg
# یا برای نسخه‌های جدید:
sudo dnf install ffmpeg
```

### macOS:
```bash
brew install ffmpeg
```

### Windows:
1. از [سایت رسمی FFmpeg](https://ffmpeg.org/download.html) دانلود کنید
2. فایل zip را استخراج کنید
3. پوشه `bin` را به PATH سیستم اضافه کنید
4. یا از Chocolatey استفاده کنید:
```bash
choco install ffmpeg
```

## روش ۳: استفاده از فایل باینری (Binary)

### دانلود باینری برای سرور:
```bash
# برای Ubuntu/Debian x64
wget https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
tar -xf ffmpeg-master-latest-linux64-gpl.tar.xz
sudo mv ffmpeg-master-latest-linux64-gpl/bin/* /usr/local/bin/
sudo chmod +x /usr/local/bin/ffmpeg
```

### تست نصب:
```bash
ffmpeg -version
```

## 🔧 تنظیمات کد برای استفاده از باینری محلی

اگر FFmpeg را در مسیر خاصی نصب کرده‌اید، می‌توانید در کد مسیر را مشخص کنید:

```python
# در bot.py، تابع _check_ffmpeg را اصلاح کنید:
def _check_ffmpeg() -> bool:
    """بررسی وجود ffmpeg در سیستم"""
    try:
        # امتحان کردن مسیرهای مختلف
        paths = ['ffmpeg', '/usr/local/bin/ffmpeg', '/usr/bin/ffmpeg']
        for path in paths:
            result = subprocess.run([path, '-version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return True
        return False
    except FileNotFoundError:
        return False
```

## ⚠️ نکات مهم

1. **حجم فایل**: فایل باینری FFmpeg حدود 40-60MB است
2. **مجوز**: FFmpeg تحت LGPL/GPL منتشر می‌شود
3. **نسخه‌ها**: همیشه از نسخه‌های جدید استفاده کنید
4. **امنیت**: فقط از منابع معتبر دانلود کنید

## 🎯 توصیه نهایی

**برای production حتماً از Docker استفاده کنید** چون:
- نیازی به دانلود فایل بزرگ ندارید
- مدیریت آسان‌تر
- محیط یکنواخت
- به‌روزرسانی ساده‌تر

## 📞 در صورت مشکل

اگر باز هم مشکل داشتید:
1. ابتدا Docker را امتحان کنید
2. اگر نشد، نصب دستی با apt/yum/brew
3. در آخرین مرحله، دانلود باینری