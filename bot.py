import os
import logging
from flask import Flask, request
from services import legacy as legacy_services
from handlers import messages

# ---------------- Logging ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------- Flask ----------------
app = Flask(__name__)

# ---------------- Legacy services ----------------
api = legacy_services.api
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN is not set in environment variables!")

# ---------------- Routes ----------------
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    logger.info(f"📩 Received update: {update}")

    if "message" in update:
        messages.handle_message(update["message"])
    elif "callback_query" in update:
        from handlers import callbacks
        callbacks.handle_callback(update["callback_query"])

    return "OK", 200

# ---------------- Main ----------------
if __name__ == "__main__":
    logger.info("🚀 Starting bot...")

    # ست کردن وبهوک
    domain = os.environ.get("DOMAIN", "mybot-production-61d8.up.railway.app")
    webhook_url = f"https://{domain}/webhook/{BOT_TOKEN}"
    try:
        resp = api.set_webhook(webhook_url)
        if resp.get("ok"):
            logger.info("✅ Webhook set successfully!")
        else:
            logger.error(f"❌ Failed to set webhook: {resp}")
    except Exception as e:
        logger.error(f"❌ Error setting webhook: {e}")

    # اجرای Flask
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
