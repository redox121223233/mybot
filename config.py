import os

# 🔑 توکن و تنظیمات از Railway ENV
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ متغیر محیطی TELEGRAM_TOKEN تنظیم نشده!")

if not WEBHOOK_URL:
    print("⚠️ WEBHOOK_URL تنظیم نشده. فقط لوکال کار میکنه")
