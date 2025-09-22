# config.py
import os

# ======= تنظیمات اصلی =======
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"   # توکن ربات
CHANNEL_USERNAME = "@redoxbot_sticker"  # یوزرنیم کانال عمومی (با @)

# مسیر ذخیره‌سازی محلی
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FONTS_DIR = os.path.join(DATA_DIR, "fonts")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)
