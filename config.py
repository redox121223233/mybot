import os

# ======= تنظیمات اصلی =======
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"
CHANNEL_USERNAME = "@redoxbot_sticker"  # کانال عمومی

# مسیر ذخیره‌سازی محلی
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FONTS_DIR = os.path.join(DATA_DIR, "fonts")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

# تنظیمات پیش‌فرض استیکر
DEFAULT_SETTINGS = {
    "font": "Vazirmatn-Regular.ttf",
    "font_size": 48,
    "font_color": "black",
    "position": "center"
}
