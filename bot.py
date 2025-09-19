
from flask import Flask, request
from utils.logger import logger
from services import legacy as legacy_services

from handlers import messages, callbacks

app = Flask(__name__)
TOKEN = legacy_services.api.token

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    logger.info("Received update: %s", update)
    if "message" in update:
        messages.handle_message(update["message"])
    elif "callback_query" in update:
        callbacks.handle_callback(update["callback_query"])
    return "ok"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
