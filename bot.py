import logging
from flask import Flask, request
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN
from handlers import messages, callbacks

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s]:%(message)s")

api = TelegramAPI(BOT_TOKEN)
app = Flask(__name__)

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.json
    logging.info(f"📩 Update received: {update}")
    try:
        if "message" in update:
            messages.handle_message(api, update["message"])
        elif "callback_query" in update:
            callbacks.handle_callback(api, update["callback_query"])
    except Exception as e:
        logging.error(f"❌ Error handling update: {e}")
    return "ok"

if __name__ == "__main__":
    logging.info("🚀 Starting bot...")
    app.run(host="0.0.0.0", port=8080)
