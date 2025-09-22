import logging
from services.sticker_manager import reset_user_settings

logger = logging.getLogger(__name__)

def handle_callback(api, callback_query):
    chat_id = callback_query["message"]["chat"]["id"]
    data = callback_query["data"]

    logger.info(f"📩 Callback received: {data}")

    if data == "reset_settings":
        reset_user_settings(chat_id)
        api.send_message(chat_id, "♻️ تنظیمات شما ریست شد.")
