from flask import Flask, request
from utils.logger import logger
from handlers import messages, callbacks, stickers

app = Flask(__name__)

@app.route(f"/webhook/<token>", methods=["POST"])
def webhook(token):
    update = request.json
    try:
        if "message" in update:
            messages.handle_message(update["message"])
        elif "callback_query" in update:
            callbacks.handle_callback(update["callback_query"])
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
