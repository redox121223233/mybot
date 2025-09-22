import logging
from flask import Flask, request
from utils.telegram_api import TelegramAPI
from handlers import messages, callbacks
from config import BOT_TOKEN

# 📌 تنظیمات لاگر
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]:%(message)s")
logger = logging.getLogger(__name__)

# 📌 ساخت Flask
app = Flask(__name__)

# 📌 ساخت API
api = TelegramAPI(BOT_TOKEN)


@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True)

    if not update:
        logger.error("❌ No update received")
        return "no update", 400

    logger.info(f"📩 Update received: {update}")

    try:
        # پیام
        if "message" in update:
            messages.handle_message(update, api)

        # کال‌بک دکمه شیشه‌ای
        elif "callback_query" in update:
            callbacks.handle_callback(update, api)

    except Exception as e:
        logger.error(f"❌ Error handling update: {e}")

    return "ok", 200


if __name__ == "__main__":
    logger.info("🚀 Starting bot...")
    app.run(host="0.0.0.0", port=8080)
