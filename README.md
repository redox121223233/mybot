# ربات استیکر ساز تلگرام

ربات تلگرام برای ساخت استیکر با متن فارسی و قابلیت‌های هوش مصنوعی

## نیازمندی‌ها

- Python 3.9 یا بالاتر
- FFmpeg (برای استیکرهای ویدیویی)

## نصب

### 1. نصب پایتون و FFmpeg

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install python3 python3-pip ffmpeg
```

#### CentOS/RHEL
```bash
sudo yum install python3 python3-pip ffmpeg
```

#### Windows
- Python را از python.org دانلود کنید
- FFmpeg را از ffmpeg.org دانلود و نصب کنید

### 2. نصب کتابخانه‌ها

```bash
pip install -r requirements.txt
```

### 3. دانلود فونت‌های فارسی

فونت‌های زیر را دانلود کرده و در پوشه `fonts/` قرار دهید:

- **Vazirmatn**: https://github.com/rastikerdar/vazirmatn/releases
  - فایل‌ها: `Vazirmatn-Regular.ttf`, `Vazirmatn-Medium.ttf`

- **Noto Naskh Arabic**: https://fonts.google.com/noto/specimen/Noto+Naskh+Arabic
  - فایل‌ها: `NotoNaskhArabic-Regular.ttf`, `NotoNaskhArabic-Medium.ttf`

- **Sahel**: https://github.com/rastikerdar/sahel-font/releases
  - فایل‌ها: `Sahel.ttf`, `Sahel-Bold.ttf`

- **IRANSans**: https://github.com/rastikerdar/iran-sans/releases
  - فایل‌ها: `IRANSans.ttf`, `IRANSansX-Regular.ttf`

**ساختار پوشه fonts:**
```
fonts/
├── Vazirmatn-Regular.ttf
├── Vazirmatn-Medium.ttf
├── NotoNaskhArabic-Regular.ttf
├── NotoNaskhArabic-Medium.ttf
├── Sahel.ttf
├── Sahel-Bold.ttf
├── IRANSans.ttf
└── IRANSansX-Regular.ttf
```

### 4. تنظیمات محیطی

فایل `.env` را ویرایش کرده و توکن ربات خود را وارد کنید:

```env
BOT_TOKEN=your_bot_token_here
```

## اجرا

### روش 1: اجرای مستقیم

```bash
python bot.py
```

### روش 2: اجرا با nohup (در پس‌زمینه)

```bash
nohup python bot.py > bot.log 2>&1 &
```

### روش 3: استفاده از systemd (پیشنهادی برای سرور)

فایل `/etc/systemd/system/telegram-bot.service` را بسازید:

```ini
[Unit]
Description=Telegram Sticker Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/project
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 /path/to/project/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

سپس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## بررسی لاگ‌ها

```bash
# اگر با nohup اجرا کرده‌اید:
tail -f bot.log

# اگر با systemd اجرا کرده‌اید:
sudo journalctl -u telegram-bot -f
```

## امکانات

- ✅ ساخت استیکر تصویری با متن فارسی
- ✅ ساخت استیکر ویدیویی با متن فارسی
- ✅ پشتیبانی از فونت‌های مختلف فارسی
- ✅ تنظیم موقعیت، رنگ و اندازه متن
- ✅ پس‌زمینه شفاف، پیش‌فرض یا سفارشی
- ✅ ساخت و مدیریت پک استیکر شخصی
- ✅ محدودیت سهمیه روزانه
- ✅ پنل ادمین

## توجه

- مطمئن شوید فونت‌های فارسی در پوشه `fonts/` قرار دارند
- برای استیکر ویدیویی، FFmpeg باید نصب باشد
- توکن ربات را از @BotFather دریافت کنید
