# راهنمای نصب FFmpeg

FFmpeg برای پردازش استیکرهای ویدیویی ضروری است.

## نصب FFmpeg

### Windows
1. از [سایت رسمی FFmpeg](https://ffmpeg.org/download.html) نسخه Windows را دانلود کنید
2. فایل zip را استخراج کنید
3. پوشه `bin` را به PATH سیستم اضافه کنید
4. یا می‌توانید از Chocolatey استفاده کنید:
   ```
   choco install ffmpeg
   ```

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

### CentOS/RHEL
```bash
sudo yum install ffmpeg
```

### macOS
```bash
brew install ffmpeg
```

## استفاده از Docker (توصیه می‌شود)

بهترین راه برای اجرای ربات استفاده از Docker است که FFmpeg به صورت خودکار نصب می‌شود:

```bash
docker build -t telegram-sticker-bot .
docker run -d --env-file .env telegram-sticker-bot
```

## تست نصب FFmpeg

برای اطمینان از نصب صحیح FFmpeg، دستور زیر را اجرا کنید:

```bash
ffmpeg -version
```

اگر FFmpeg به درستی نصب شده باشد، اطلاعات نسخه نمایش داده می‌شود.