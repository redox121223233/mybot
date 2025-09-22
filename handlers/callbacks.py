# handlers/callbacks.py
import logging
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI
from services.setting_manager import reset_user_settings   # ✅ اصلاح شد
from handlers.messages import send_main_menu

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# ------------------ مدیریت کال‌بک‌ها ------------------
def handle_callback(callback_query):
    chat_id = callback_query["message"]["chat"]["id"]
    user_id = callback_query["from"]["id"]
    data = callback_query["data"]

    logger.info(f"📩 handle_callback {user_id}: {data}")

    try:
        if data == "reset_settings":
            reset_user_settings(user_id)
            api.send_message(chat_id, "🔄 تنظیمات شما به حالت اولیه بازنشانی شد.")
            send_main_menu(chat_id)
        else:
            api.send_message(chat_id, "❓ گزینه ناشناخته است.")

    except Exception as e:
        logger.error(f"❌ Error in handle_callback: {e}")
        api.send_message(chat_id, "❌ خطایی در پردازش درخواست شما رخ داد.")
