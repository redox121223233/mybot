# handlers/callbacks.py
import logging
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI
from handlers.messages import send_main_menu

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

def handle_callback(callback_query):
    # این پروژه با ReplyKeyboard کار می‌کند؛ callbackها کمتر استفاده می‌شوند
    try:
        chat_id = callback_query["message"]["chat"]["id"]
        data = callback_query["data"]
        logger.info(f"callback {chat_id}: {data}")
        if data == "main_menu":
            send_main_menu(chat_id)
        else:
            api.send_message(chat_id, "دستور نامشخص از دکمه شیشه‌ای.")
    except Exception as e:
        logger.error(f"callback error: {e}")
