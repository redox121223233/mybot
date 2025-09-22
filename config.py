import os

# ======= تنظیمات اصلی =======
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"

# 👇 فقط نام کانال (بدون @) - ربات باید ادمین یا عضو کانال باشه
CHANNEL_USERNAME = "redoxbot_sticker"

# ======= مسیرها =======
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FONTS_DIR = os.path.join(DATA_DIR, "fonts")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)
