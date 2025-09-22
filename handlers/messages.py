import logging
from config import CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI
from utils.ai_manager import generate_sticker
from utils.sticker_manager import save_user_settings, get_user_settings

api = TelegramAPI()

logger = logging.getLogger(__name__)

def handle_message(message):
    user_id = message["from"]["id"]
    text = message.get("text", "")

    logger.info(f"📩 handle_message {user_id}: {text}")

    if text == "/start":
        api.send_message(user_id, "سلام! به ربات خوش اومدی 🎉")
        # اینجا منوی اصلی رو نشون بده
    elif text == "🎭 استیکرساز":
        api.send_message(user_id, "🖼 یک متن یا عکس بفرست تا برات استیکر بسازم!")
    elif text == "🤖 هوش مصنوعی":
        api.send_message(user_id, "🧠 متن خلاقانه‌تو بفرست تا برات استیکر هوشمند بسازم!")
    else:
        api.send_message(user_id, "❌ متوجه نشدم. لطفا از منو انتخاب کن.")
