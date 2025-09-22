# handlers/callbacks.py
import logging
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI
from services.setting_manager import reset_user_settings   # ✅ مسیر درست
from services.menu_manager import get_main_menu

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# ------------------ مدیریت کال‌بک‌ها ------------------
def handle_callback(callback_query):
    query_id = callback_query["id"]
    user_id = callback_query["from"]["id"]
    data = callback_query.get("data", "")

    logger.info(f"📩 handle_callback {user_id}: {data}")

    if data == "reset_settings":
        reset_user_settings(user_id)
        api.send_message(
            user_id,
            "✅ تنظیمات شما بازنشانی شد.",
            reply_markup=get_main_menu()
        )
    elif data == "back_to_menu":
        api.send_message(
            user_id,
            "🏠 منوی اصلی:",
            reply_markup=get_main_menu()
        )
    else:
        logger.warning(f"⚠️ ناشناخته: {data}")
        api.send_message(user_id, "❌ گزینه نامعتبر است.")
