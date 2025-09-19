from flask import Flask, request
from utils.logger import logger
from handlers import messages, callbacks
from services.legacy import api

app = Flask(__name__)

@app.route(f"/{api.token}", methods=["POST"])
def webhook():
    update = request.get_json()
    logger.info(f"Received update: {update}")

    if "message" in update:
        messages.handle_message(update["message"])
    elif "callback_query" in update:
        callbacks.handle_callback(update["callback_query"])

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
