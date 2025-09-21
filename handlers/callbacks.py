import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN   # ✅ اضافه شد

api = TelegramAPI(BOT_TOKEN)   # ✅ ساخت api با توکن
logger = logging.getLogger(__name__)

def handle_callback(callback_query):
    user_id = callback_query["from"]["id"]
    data = callback_query.get("data", "")

    logger.info(f"🔘 Callback from {user_id}: {data}")

    if data == "back_to_menu":
        from handlers import messages
        messages.main_menu(user_id)
