# handlers/callbacks.py
import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN, CHANNEL_USERNAME
from handlers.messages import send_main_menu

api = TelegramAPI(BOT_TOKEN)
logger = logging.getLogger(__name__)

def handle_callback(callback_query):
    chat_id = callback_query["message"]["chat"]["id"]
    user_id = callback_query["from"]["id"]
    data = callback_query["data"]

    logger.info(f"📩 handle_callback {user_id}: {data}")

    if data == "check_membership":
        if api.is_user_in_channel(user_id):
            api.send_message(chat_id, "✅ عضویت شما تایید شد.")
            send_main_menu(chat_id)
        else:
            api.send_message(
                chat_id,
                f"❌ هنوز عضو کانال نیستید!\n{CHANNEL_USERNAME}",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "📢 عضویت در کانال", "url": f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"}],
                        [{"text": "✅ بررسی مجدد", "callback_data": "check_membership"}]
                    ]
                }
            )
