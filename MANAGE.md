# راهنمای مدیریت ربات

این راهنما برای مدیریت و نگهداری ربات استیکر ساز تلگرام است.

## 🔄 کنترل ربات

### با systemd (پیشنهادی)

```bash
# شروع ربات
sudo systemctl start telegram-bot

# توقف ربات
sudo systemctl stop telegram-bot

# ریستارت ربات
sudo systemctl restart telegram-bot

# وضعیت ربات
sudo systemctl status telegram-bot

# مشاهده لاگ‌ها
sudo journalctl -u telegram-bot -f

# مشاهده ۱۰۰ خط آخر لاگ
sudo journalctl -u telegram-bot -n 100
```

### با nohup

```bash
# اجرا
nohup python3 bot.py > bot.log 2>&1 &

# پیدا کردن Process ID
ps aux | grep bot.py

# توقف ربات
kill <PID>

# مشاهده لاگ
tail -f bot.log
```

### با screen

```bash
# ساخت session جدید
screen -S telegram-bot

# اجرای ربات
python3 bot.py

# جدا شدن از session (Ctrl+A سپس D)

# بازگشت به session
screen -r telegram-bot

# لیست session‌ها
screen -ls
```

## 📊 مانیتورینگ

### بررسی وضعیت ربات

```bash
# بررسی Process
ps aux | grep bot.py

# بررسی استفاده از CPU و RAM
top -p $(pgrep -f bot.py)

# بررسی فضای دیسک
df -h

# بررسی استفاده از RAM
free -h
```

### لاگ‌ها

```bash
# مشاهده زنده لاگ (systemd)
sudo journalctl -u telegram-bot -f

# مشاهده لاگ (nohup)
tail -f bot.log

# جستجو در لاگ‌ها
grep "ERROR" bot.log
grep "خطا" bot.log
```

## 🔧 تنظیمات پیشرفته

### تغییر پورت یا تنظیمات

فایل `bot.py` را ویرایش کنید:

```python
# تغییر تعداد سهمیه روزانه
DAILY_LIMIT = 5  # به عدد دلخواه تغییر دهید

# حالت نگهداری
MAINTENANCE = False  # True برای فعال کردن

# کانال عضویت اجباری
CHANNEL_USERNAME = "@your_channel"

# ID ادمین
ADMIN_ID = 123456789
```

بعد از تغییرات، ربات را ریستارت کنید:

```bash
sudo systemctl restart telegram-bot
```

### بک‌آپ داده‌ها

ربات داده‌ها را در حافظه نگه می‌دارد. برای ذخیره دائمی، می‌توانید:

```bash
# بک‌آپ کل پروژه
tar -czf backup-$(date +%Y%m%d).tar.gz .

# بک‌آپ فقط فایل‌های مهم
tar -czf backup-$(date +%Y%m%d).tar.gz bot.py .env fonts/
```

### بروزرسانی ربات

```bash
# 1. توقف ربات
sudo systemctl stop telegram-bot

# 2. بک‌آپ نسخه فعلی
cp bot.py bot.py.backup

# 3. بروزرسانی فایل‌ها
# (کپی فایل جدید یا git pull)

# 4. شروع ربات
sudo systemctl start telegram-bot

# 5. بررسی لاگ
sudo journalctl -u telegram-bot -f
```

## 🐛 عیب‌یابی

### ربات ریستارت می‌شود

```bash
# بررسی لاگ‌ها
sudo journalctl -u telegram-bot -n 200

# علل احتمالی:
# - خطا در کد
# - مشکل شبکه
# - نبود توکن در .env
# - نبود فونت‌ها
```

### استفاده بالای RAM

```bash
# بررسی استفاده از حافظه
ps aux | grep bot.py

# اگر RAM زیاد مصرف می‌شود:
# - تعداد کاربران را محدود کنید
# - حافظه cache را پاک کنید
# - ربات را ریستارت کنید
sudo systemctl restart telegram-bot
```

### ربات پاسخ نمی‌دهد

```bash
# 1. بررسی وضعیت
sudo systemctl status telegram-bot

# 2. بررسی لاگ‌ها
sudo journalctl -u telegram-bot -f

# 3. بررسی اتصال اینترنت
ping telegram.org

# 4. ریستارت ربات
sudo systemctl restart telegram-bot
```

## 🔐 امنیت

### محافظت از توکن

```bash
# مطمئن شوید .env در .gitignore است
cat .gitignore | grep .env

# تنظیم دسترسی‌های فایل
chmod 600 .env
```

### محدود کردن دسترسی

```bash
# اجرای ربات با کاربر غیر root
sudo useradd -m -s /bin/bash telegram-bot
sudo chown -R telegram-bot:telegram-bot /path/to/project

# ویرایش فایل service
sudo nano /etc/systemd/system/telegram-bot.service
# تغییر: User=telegram-bot
```

## 📈 بهینه‌سازی

### کاهش استفاده از RAM

در `bot.py`:

```python
# محدود کردن تعداد session‌های ذخیره شده
MAX_SESSIONS = 1000

# پاک‌سازی session‌های قدیمی
def cleanup_old_sessions():
    # کد پاک‌سازی
    pass
```

### افزایش سرعت

```bash
# استفاده از PyPy به جای CPython
sudo apt install pypy3
pypy3 -m pip install -r requirements.txt
pypy3 bot.py
```

## 🔔 اعلان‌ها

### دریافت اعلان در صورت خطا

می‌توانید یک کانال یا گروه تلگرام برای لاگ‌ها بسازید و خطاها را به آن ارسال کنید.

در `bot.py`:

```python
LOG_CHANNEL = -1001234567890  # ID کانال لاگ

async def log_error(text: str):
    try:
        await bot.send_message(LOG_CHANNEL, f"❌ خطا:\n{text}")
    except:
        pass
```

## 📞 پشتیبانی

در صورت نیاز به کمک:
- لاگ‌ها را بررسی کنید
- Issue در GitHub ایجاد کنید
- با پشتیبانی تماس بگیرید
