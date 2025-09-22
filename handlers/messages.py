import logging
from config import CHANNEL_USERNAME
from services.ai_manager import generate_sticker
from services.sticker_manager import handle_sticker_upload
from utils.settings_manager import update_user_settings, reset_user_settings

logger = logging.getLogger(__name__)

def handle_message(api, message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    photos = message.get("photo")

    logger.info(f"📩 handle_message {chat_id}: {text}")

    # Start
    if text == "/start":
        if not api.is_user_in_channel(CHANNEL_USERNAME, chat_id):
            api.send_message(
                chat_id,
                f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n{CHANNEL_USERNAME}\n\nسپس /start را بزنید ✅"
            )
            return
        send_main_menu(api, chat_id)

    # Sticker maker
    elif text == "🎭 استیکرساز":
        api.send_message(chat_id, "🖼 لطفا عکس مورد نظر را ارسال کنید تا استیکر ساخته شود.")

    elif photos:
        handle_sticker_upload(api, chat_id, photos)

    # AI
    elif text == "🤖 هوش مصنوعی":
        api.send_message(chat_id, "✍️ متن یا دستور خود را بفرستید تا تبدیل به استیکر شود.")

    elif text.startswith("تنظیمات"):
        api.send_message(chat_id, "⚙️ تنظیمات استیکر به‌زودی فعال می‌شود.")

    else:
        api.send_message(chat_id, "❓ متوجه نشدم. لطفا از منوی اصلی استفاده کنید.")

def send_main_menu(api, chat_id):
    reply_markup = {
        "keyboard": [
            [{"text": "🎭 استیکرساز"}],
            [{"text": "🤖 هوش مصنوعی"}],
            [{"text": "⚙️ تنظیمات"}, {"text": "♻️ ریست تنظیمات"}]
        ],
        "resize_keyboard": True
    }
    api.send_message(chat_id, "👋 به ربات خوش آمدید!\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=reply_markup)
