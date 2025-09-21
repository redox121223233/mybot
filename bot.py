import logging
import requests
from flask import Flask, request
from services import legacy as legacy_services
from handlers import messages

# ---------------- CONFIG ----------------
BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"
APP_URL = "https://mybot-production-61d8.up.railway.app"  # دامین Railway

# ---------------- LOGGER ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s,%(msecs)03d %(levelname)s:%(message)s")
logger = logging.getLogger(__name__)

# ---------------- FLASK ----------------
app = Flask(__name__)

# ---------------- WEBHOOK ----------------
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    logger.info(f"📩 Received update: {update}")

    if "message" in update:
        try:
            messages.handle_message(update["message"])
        except Exception as e:
            logger.error(f"❌ Error in handle_message: {e}")

    return "OK", 200


# ---------------- SET WEBHOOK ----------------
def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    data = {"url": f"{APP_URL}/{BOT_TOKEN}"}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        logger.info("✅ Webhook set successfully!")
    else:
        logger.error(f"❌ Failed to set webhook: {response.text}")


# ---------------- MAIN ----------------
if __name__ == "__main__":
    logger.info("🚀 Starting bot...")
    set_webhook()
    app.run(host="0.0.0.0", port=5000)
 logging
from flask import Flask, request
from services import legacy as legacy_services
from handlers import messages

# لاگر
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

# فلَسک
app = Flask(__name__)

# توکن ربات از legacy
from config import BOT_TOKEN
TOKEN = BOT_TOKEN
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
