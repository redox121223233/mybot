import logging
from config import BOT_TOKEN, CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)


# ------------------ منوی اصلی ------------------
def send_main_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🤖 هوش مصنوعی", "callback_data": "ai"}],
            [{"text": "🎭 استیکرساز", "callback_data": "sticker"}],
            [{"text": "ℹ️ راهنما", "callback_data": "help"}]
        ]
    }

    api.send_message(
        chat_id,
        "👋 خوش اومدی! از منوی زیر یکی رو انتخاب کن:",
        reply_markup=keyboard
    )


# ------------------ پیام‌های ورودی ------------------
def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = message["from"]["id"]

    logger.info(f"📩 handle_message {chat_id}: {text}")

    # بررسی عضویت
    if not api.is_user_in_channel(CHANNEL_USERNAME, user_id):
        api.send_message(
            chat_id,
            f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n@{CHANNEL_USERNAME}\n\nسپس /start را بزنید ✅"
        )
        return

    # دستور /start
    if text == "/start":
        send_main_menu(chat_id)
        return

    # ورودی‌های غیر از دستور
    api.send_message(chat_id, "❌ دستور ناشناخته. از منو استفاده کن:")
    send_main_menu(chat_id)
