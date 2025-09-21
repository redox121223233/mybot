# config.py
import os

# ======= تنظیمات اصلی =======
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"   # <-- اینجا توکن ربات رو بذار
CHANNEL_USERNAME = "@redoxbot_sticker"  # مثلاً "redoxBOT_STICKER" (بدون @ یا با @ هر دو پشتیبانی میشه)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")  # مسیر ذخیره‌سازی محلی
FONTS_DIR = os.path.join(DATA_DIR, "fonts")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

