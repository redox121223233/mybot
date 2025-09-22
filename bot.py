import logging
from flask import Flask, request
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI
from handlers import messages

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]:%(message)s")
app = Flask(__name__)
api = TelegramAPI(BOT_TOKEN)

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    logging.info(f"📩 Update received: {update}")

    try:
        if "message" in update:
            messages.handle_message(update["message"])
    except Exception as e:
        logging.error(f"❌ Error handling update: {e}")

    return "ok", 200

if __name__ == "__main__":
    logging.info("🚀 Starting bot...")
    try:
        resp = api.set_webhook(f"https://mybot-production-61d8.up.railway.app/webhook/{BOT_TOKEN}")
        logging.info(f"✅ Webhook set successfully: {resp}")
    except Exception as e:
        logging.error(f"❌ Error setting webhook: {e}")

    app.run(host="0.0.0.0", port=8080)
