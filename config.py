import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "اینجا توکن رباتت")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ساخت پوشه دیتا در صورت نیاز
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
