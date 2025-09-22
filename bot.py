# bot.py
import logging
import os
from flask import Flask, request
from utils.telegram_api import TelegramAPI
from handlers import messages, callbacks
from config import BOT_TOKEN

# 📌 لاگ‌گیری
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]:%(message)s",
)
logger = logging.getLogger(__name__)

# 📌 راه‌اندازی تلگرام API
api = TelegramAPI(BOT_TOKEN)

# 📌 وب‌سرور
app = Flask(__name__)

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    logger.info(f"📩 Update received: {update}")

    try:
        if "message" in update:
            messages.handle_message(update)   # ✅ فقط update پاس میدیم
        elif "callback_query" in update:
            callbacks.handle_callback(update) # ✅ فقط update پاس میدیم
    except Exception as e:
        logger.error(f"❌ Error handling update: {e}", exc_info=True)

    return "OK", 200


if __name__ == "__main__":
    logger.info("🚀 Starting bot...")

    # 📌 ست کردن وبهوک
    try:
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            api.request("setWebhook", {"url": f"{webhook_url}/webhook/{BOT_TOKEN}"})
            logger.info("✅ Webhook set successfully")
        else:
            logger.warning("⚠️ WEBHOOK_URL تنظیم نشده. فقط لوکال کار میکنه.")

    except Exception as e:
        logger.error(f"❌ خطا در تنظیم وبهوک: {e}", exc_info=True)

    # 📌 اجرای Flask
    app.run(host="0.0.0.0", port=8080)
