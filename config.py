import os

# ======= تنظیمات اصلی =======
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"   # توکن واقعی ربات
CHANNEL_USERNAME = "redoxbot_sticker"  # بدون @ بزن

# ======= تنظیمات وبهوک =======
DOMAIN = "https://mybot-production-61d8.up.railway.app"  # دامین Railway
WEBHOOK_URL = f"{DOMAIN}/webhook/{BOT_TOKEN}"

# ======= مسیرهای ذخیره‌سازی =======
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FONTS_DIR = os.path.join(DATA_DIR, "fonts")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)
