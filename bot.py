import os
import logging
from flask import Flask, request
from services import legacy as legacy_services
from config import BOT_TOKEN

# ⚡ لاگینگ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ⚡ Flask
app = Flask(__name__)

# ⚡ سرویس‌ها
api = legacy_services.api
menu_manager = legacy_services.menu_manager
sticker_manager = legacy_services.sticker_manager
ai_manager = legacy_services.ai_manager
subscription_manager = legacy_services.subscription_manager

# 🌍 گرفتن دامین از محیط Railway
DOMAIN = os.getenv("DOMAIN", "mybot-production-61d8.up.railway.app")

# ⚡ مسیر وبهوک درست
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return {"ok": True}

    if "message" in update:
        from handlers import messages
        messages.handle_message(update["message"])

    elif "callback_query" in update:
        from handlers import callbacks
        callbacks.handle_callback(update["callback_query"])

    return {"ok": True}


if __name__ == "__main__":
    logger.info("🚀 Starting bot...")

    # 🔹 ست کردن وبهوک درست
    webhook_url = f"https://{DOMAIN}/webhook/{BOT_TOKEN}"
    resp = api.set_webhook(webhook_url)
    if resp.get("ok"):
        logger.info("✅ Webhook set successfully!")
    else:
        logger.error(f"❌ Error setting webhook: {resp}")

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
