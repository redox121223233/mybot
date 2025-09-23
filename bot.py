from flask import Flask, request
from handlers import messages
from config import TELEGRAM_TOKEN, WEBHOOK_URL
from services.telegram_api import TelegramAPI

app = Flask(__name__)
api = TelegramAPI(TELEGRAM_TOKEN)

@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()
    messages.handle_message(api, update)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
