# bot.py
import os
from flask import Flask, request
from utils.logger import logger
from utils.telegram_api import register_webhook
from handlers import messages, callbacks

BOT_TOKEN = os.environ.get("BOT_TOKEN")
APP_URL = os.environ.get("APP_URL")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set in environment variables")

app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True)
    if not update:
        return "no update"

    logger.info(f"Received update: {update}")

    if "message" in update:
        messages.process_message(update["message"])
    elif "callback_query" in update:
        callbacks.handle_callback_query(update["callback_query"])

    return "ok"


if __name__ == "__main__":
    # ثبت وبهوک در استارتاپ
    if APP_URL:
        logger.info(f"Setting webhook for {APP_URL}/{BOT_TOKEN}")
        register_webhook(APP_URL, secret_token="stickerbot")
    else:
        logger.warning("⚠️ APP_URL not set, webhook not registered")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
