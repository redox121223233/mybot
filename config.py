# config.py
import os

BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# لینک کانال اجباری
CHANNEL_LINK = "@redoxbot_sticker"  # هم با @ هم بدون @ پشتیبانی میشه

# مسیر دیتا
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FONTS_DIR = os.path.join(DATA_DIR, "fonts")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)
