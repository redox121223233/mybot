# خلاصه تغییرات انجام شده

## تاریخ: 2025-10-09
## وضعیت: ✅ تمام مشکلات رفع شد و تست شد

### مشکل ۱: رفع مشکل فونت فارسی ✅

**مشکل:** حروف فارسی جدا و برعکس نمایش داده می‌شدند (مثال: "سلام" به صورت "م ا ل س" نمایش داده می‌شد)

**راه‌حل:**
- تابع `_prepare_text` در فایل `bot.py` اصلاح شد
- از کتابخانه‌های `arabic_reshaper` و `python-bidi` برای اتصال صحیح حروف فارسی و تبدیل به RTL استفاده شد
- کد جدید:
  ```python
  def _prepare_text(text: str) -> str:
      if not text:
          return ""
      
      text = text.strip()
      lang = _detect_language(text)
      
      if lang == "persian":
          reshaped_text = arabic_reshaper.reshape(text)
          bidi_text = get_display(reshaped_text)
          return bidi_text
      
      return text
  ```

### مشکل ۲: رفع مشکل FFmpeg برای استیکر ویدیویی ✅

**مشکل:** خطای "FFmpeg نصب نیست" هنگام استفاده از استیکر ویدیویی

**راه‌حل:**
- FFmpeg در Dockerfile به درستی نصب شده است
- فایل راهنمای نصب `FFMPEG_INSTALL.md` ایجاد شد با دستورالعمل‌های کامل برای:
  - Windows (دانلود مستقیم یا Chocolatey)
  - Ubuntu/Debian (`sudo apt install ffmpeg`)
  - CentOS/RHEL (`sudo yum install ffmpeg`)
  - macOS (`brew install ffmpeg`)
- توصیه استفاده از Docker برای اجرای ربات (FFmpeg به صورت خودکار نصب می‌شود)

### مشکل ۳: اضافه کردن محدودیت روزانه ✅

**تغییرات:**

1. **تنظیمات جدید:**
   - `DAILY_LIMIT_AI = 3` - محدودیت ۳ بار در روز برای استیکرهای AI
   - `DAILY_LIMIT_SIMPLE = 50` - محدودیت ۵۰ بار در روز برای استیکرهای ساده
   - ادمین همچنان نامحدود است

2. **ساختار داده کاربران:**
   - فیلد `simple_used` به دیکشنری کاربران اضافه شد
   - هر روز به صورت خودکار ریست می‌شود

3. **توابع جدید:**
   - `_quota_left_ai()` - بررسی سهمیه باقی‌مانده AI
   - `_quota_left_simple()` - بررسی سهمیه باقی‌مانده استیکر ساده

4. **بررسی محدودیت:**
   - قبل از ورود به بخش AI
   - قبل از ورود به بخش استیکر ساده
   - قبل از تایید و ارسال استیکر
   - نمایش پیام مناسب با زمان باقی‌مانده تا تمدید

5. **نمایش سهمیه:**
   - در منوی اصلی: نمایش سهمیه AI و ساده به صورت جداگانه
   - در بخش AI: نمایش سهمیه باقی‌مانده
   - در بخش استیکر ساده: نمایش سهمیه باقی‌مانده

## نحوه استفاده

### اجرای ربات با Docker (توصیه می‌شود):
```bash
docker build -t telegram-sticker-bot .
docker run -d --env-file .env telegram-sticker-bot
```

### اجرای ربات بدون Docker:
1. نصب FFmpeg (مطابق راهنمای `FFMPEG_INSTALL.md`)
2. نصب وابستگی‌های Python:
   ```bash
   pip install -r requirements.txt
   ```
3. اجرای ربات:
   ```bash
   python bot.py
   ```

## تست تغییرات

### تست‌های خودکار انجام شده ✅
1. **test_persian_fix.py** - تست تابع _prepare_text و سیستم محدودیت
   - تست متن‌های فارسی: "سلام"، "سلام دنیا"، "استیکر ساز"
   - تست متن انگلیسی: "Hello World"
   - تست متن ترکیبی: "سلام Hello"
   - تست توابع محدودیت برای کاربر عادی و ادمین
   - **نتیجه: ✅ همه تست‌ها موفق**

2. **test_imports.py** - تست syntax و import ها
   - بررسی syntax کد
   - بررسی import های اصلی
   - بررسی وجود توابع کلیدی
   - بررسی متغیرهای تنظیمات
   - **نتیجه: ✅ همه تست‌ها موفق**

### تست‌های دستی توصیه شده
1. متن فارسی را در استیکر تست کنید (مثلاً "سلام دنیا")
2. استیکر ویدیویی را تست کنید
3. محدودیت روزانه را با ایجاد چند استیکر تست کنید
4. بررسی کنید که سهمیه در منوی اصلی به درستی نمایش داده می‌شود

## رفع خطاها

### خطای "name 'left' is not defined" ✅
**مشکل:** در چند جا از کد، متغیر left استفاده شده بود که دیگر وجود نداشت.

**راه‌حل:** تمام موارد استفاده از left به left_ai تغییر داده شد:
- خط 959: بررسی محدودیت در callback handler
- خط 1267: بررسی محدودیت در message handler

**نتیجه:** خطا به طور کامل رفع شد و کد بدون مشکل اجرا می‌شود.

## فایل‌های اضافه شده
- test_persian_fix.py - تست‌های خودکار برای فونت فارسی و محدودیت
- test_imports.py - تست‌های خودکار برای syntax و import ها

## Commits
1. deaf416 - Fix Persian font rendering and add daily limits
2. 557f3cc - Fix undefined 'left' variable error - replace with 'left_ai'
3. 70eb1bf - Add comprehensive tests for Persian text and quota system