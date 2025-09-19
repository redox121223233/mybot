from flask import Flask, request, jsonify
from utils.logger import logger
from handlers import messages, callbacks

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status":"ok"})

@app.route("/webhook/<token>", methods=["POST"])
def webhook(token):
    update = request.get_json(force=True)
    logger.info(f"Received update for token={token}: {str(update)[:800]}")
    try:
        if "callback_query" in update:
            callbacks.handle_callback(update["callback_query"])
        if "message" in update:
            messages.handle_message(update["message"])
    except Exception as e:
        logger.error("Error in webhook dispatch: %s", e)
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
