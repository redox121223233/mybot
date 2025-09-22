# handlers/callbacks.py
import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN, CHANNEL_USERNAME
from handlers.messages import send_main_menu

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

def handle_callback(callback_query: dict):
    data = callback_query.get("data")
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]

    logger.info(f"📩 handle_callback {user_id}: {data}")

    if data == "check_membership":
        try:
            if api.is_user_in_channel(CHANNEL_USERNAME, user_id):
                api.send_message(chat_id, "✅ عضویت شما تایید شد. حالا می‌توانید از ربات استفاده کنید.")
                send_main_menu(chat_id)
            else:
                api.send_message(chat_id, f"❌ هنوز عضو نبودی. لطفاً ابتدا در کانال عضو شوید:\n{CHANNEL_USERNAME}")
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            api.send_message(chat_id, "❌ مشکلی در بررسی عضویت پیش آمد. بعداً دوباره امتحان کنید.")
