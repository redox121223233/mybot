import os
import logging
from flask import Flask, request
from services import legacy as legacy_services
from handlers import messages, callbacks

# ---------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------- Init ----------------
app = Flask(__name__)
api = legacy_services.api
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ---------------- Routes ----------------
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    """دریافت آپدیت‌های تلگرام"""
    try:
        update = request.get_json(force=True, silent=True)
        if not update:
            return "no update", 200

        logger.info(f"📩 Received update: {update}")

        if "message" in update:
            messages.handle_message(update["message"])
        elif "callback_query" in update:
            callbacks.handle_callback(update["callback_query"])

        return "ok", 200
    except Exception as e:
        logger.exception(f"❌ Error in webhook: {e}")
        return "error", 200  # همیشه جواب بدیم تا تلگرام retry نکنه

@app.route("/", methods=["GET"])
def home():
    return "🤖 Bot is running!", 200

# ---------------- Main ----------------
if __name__ == "__main__":
    logger.info("🚀 Starting bot...")

    # ست کردن وبهوک
    webhook_url = f"https://mybot-production-61d8.up.railway.app/webhook/{BOT_TOKEN}"
    try:
        resp = api.request("setWebhook", {"url": webhook_url})
        if resp.get("ok"):
            logger.info("✅ Webhook set successfully!")
        else:
            logger.error(f"❌ Failed to set webhook: {resp}")
    except Exception as e:
        logger.error(f"❌ Error setting webhook: {e}")

    # اجرای Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
