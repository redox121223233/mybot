import logging
from flask import Flask, request
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI
from handlers import messages, callbacks

# ------------------ تنظیمات ------------------
DOMAIN = "https://mybot-production-61d8.up.railway.app"
WEBHOOK_URL = f"{DOMAIN}/webhook/{BOT_TOKEN}"

# ------------------ لاگر ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]:%(message)s"
)

# ------------------ Flask ------------------
app = Flask(__name__)
api = TelegramAPI(BOT_TOKEN)

# ------------------ Route وبهوک ------------------
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    logging.info(f"📩 Update received: {update}")

    try:
        if "message" in update:
            messages.handle_message(update["message"])
        elif "callback_query" in update:
            callbacks.handle_callback(update["callback_query"])
    except Exception as e:
        logging.error(f"❌ Error handling update: {e}")

    return "ok", 200

# ------------------ اجرای اصلی ------------------
if __name__ == "__main__":
    logging.info("🚀 Starting bot...")

    # ست کردن وبهوک
    try:
        resp = api.set_webhook(WEBHOOK_URL)
        logging.info(f"✅ Webhook set successfully: {resp}")
    except Exception as e:
        logging.error(f"❌ Error setting webhook: {e}")

    app.run(host="0.0.0.0", port=8080)
