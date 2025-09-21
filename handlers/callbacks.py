import logging
from utils.telegram_api import TelegramAPI
from config import CHANNEL_LINK

api = TelegramAPI()

logger = logging.getLogger(__name__)

# ➖➖ منوی اصلی ➖➖
def main_menu(user_id):
    keyboard = {
        "keyboard": [
            ["🎭 استیکر ساز"],
            ["🤖 هوش مصنوعی"],
            ["ℹ️ درباره ما"]
        ],
        "resize_keyboard": True
    }
    api.send_message(user_id, "📍 منوی اصلی:", reply_markup=keyboard)

# ➖➖ هندل پیام‌ها ➖➖
def handle_message(message):
    user_id = message["from"]["id"]
    text = message.get("text", "")

    logger.info(f"📩 handle_message {user_id}: {text}")

    # 🔐 عضویت اجباری
    if not api.is_user_in_channel(user_id, CHANNEL_LINK):
        join_button = {
            "inline_keyboard": [[{"text": "عضویت در کانال ✅", "url": CHANNEL_LINK}]]
        }
        api.send_message(user_id, "برای استفاده از ربات باید در کانال عضو شوید 👇", reply_markup=join_button)
        return

    # دستورات
    if text == "/start":
        main_menu(user_id)

    elif text == "🎭 استیکر ساز":
        api.send_message(
            user_id,
            "📦 نام پک استیکر خود را وارد کنید:",
            reply_markup={"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}
        )
        # اینجا StickerManager وارد عمل میشه

    elif text == "🤖 هوش مصنوعی":
        api.send_message(
            user_id,
            "✍️ پیام خود را وارد کنید تا هوش مصنوعی پاسخ دهد:",
            reply_markup={"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}
        )
        # اینجا AIManager وارد عمل میشه

    elif text == "⬅️ بازگشت":
        main_menu(user_id)

    else:
        api.send_message(user_id, "❓ متوجه نشدم. از منو استفاده کنید.")
