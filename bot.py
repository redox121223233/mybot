import os
import logging
from flask import Flask, request
from services import legacy as legacy_services
from handlers import messages, callbacks
from config import BOT_TOKEN

# ---------------------- Logging ----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------- Flask ----------------------
app = Flask(__name__)
api = legacy_services.api

# ---------------------- Webhook ----------------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """تلگرام اینجا آپدیت‌ها رو می‌فرسته"""
    update = request.get_json(force=True, silent=True)

    if not update:
        logger.warning("⚠️ دریافت آپدیت خالی از تلگرام")
        return "no update", 200

    logger.info(f"📩 Update: {update}")

    try:
        if "message" in update:
            messages.handle_message(update["message"])
        elif "callback_query" in update:
            callbacks.handle_callback(update["callback_query"])
    except Exception as e:
        logger.error(f"❌ Error handling update: {e}")

    return "ok", 200   # ✅ مهم: همیشه جواب بده

# ---------------------- Startup ----------------------
if __name__ == "__main__":
    logger.info("🚀 Starting bot...")

    # ست وبهوک
    webhook_url = f"https://mybot-production-61d8.up.railway.app/{BOT_TOKEN}"
    api.set_webhook(webhook_url)
    logger.info("✅ Webhook set successfully!")

    # اجرای Flask روی Railway
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
