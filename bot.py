import logging
from flask import Flask, request
from services import legacy as legacy_services
from handlers import messages

# لاگر
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

# فلَسک
app = Flask(__name__)

# توکن ربات از legacy
TOKEN = legacy_services.api.BOT_TOKEN

# مسیر وبهوک
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    logging.info(f"Received update: {update}")

    if "message" in update:
        messages.handle_message(update["message"])
    elif "callback_query" in update:
        # در صورت نیاز کال‌بک‌ها هم اینجا هندل میشن
        pass

    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
