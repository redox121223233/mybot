# handlers/messages.py
import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN, CHANNEL_USERNAME

api = TelegramAPI(BOT_TOKEN)
logger = logging.getLogger(__name__)

# 📌 نمایش منوی اصلی
def send_main_menu(chat_id):
    api.send_message(
        chat_id,
        "سلام 👋\nبه ربات خوش اومدی!\nیکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup={
            "keyboard": [
                [{"text": "🎭 استیکرساز"}],
                [{"text": "🤖 هوش مصنوعی"}],
            ],
            "resize_keyboard": True
        }
    )

# 📌 هندل پیام‌ها
def handle_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    logger.info(f"📩 handle_message {user_id}: {text}")

    # چک عضویت در کانال
    if not api.is_user_in_channel(user_id):
        api.send_message(
            chat_id,
            f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n{CHANNEL_USERNAME}\n\nسپس /start را بزنید ✅",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📢 عضویت در کانال", "url": f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"}],
                    [{"text": "✅ بررسی مجدد", "callback_data": "check_membership"}]
                ]
            }
        )
        return

    # اگر عضو بود:
    if text == "/start":
        send_main_menu(chat_id)
