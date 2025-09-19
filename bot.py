from flask import Flask, request, jsonify
from utils.logger import logger
from handlers import messages, callbacks
from utils.telegram_api import register_webhook

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
            messages.process_message = getattr(messages, 'process_message', None)
            # messages.handle_message is preferred; if not present, call messages.process_message
            if hasattr(messages, 'handle_message'):
                messages.handle_message(update["message"])
            elif callable(messages.process_message):
                messages.process_message(update["message"])
    except Exception as e:
        logger.error("Error in webhook dispatch: %s", e)
    return "OK", 200

if __name__ == '__main__':
    # attempt to register webhook if function exists
    try:
        register_webhook()
    except Exception:
        pass
    app.run(host='0.0.0.0', port=8080)
