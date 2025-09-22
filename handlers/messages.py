import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN, CHANNEL_USERNAME
from services.sticker_manager import handle_sticker_upload
from services.ai_manager import generate_sticker
from services.setting_manager import get_user_settings

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)


# ------------------ منوی اصلی ------------------
def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🎭 استیکرساز"],
            ["🤖 هوش مصنوعی"]
        ],
        "resize_keyboard": True
    }
    api.send_message(
        chat_id,
        "👋 به ربات خوش آمدید!\nیکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=keyboard
    )


# ------------------ مدیریت پیام‌ها ------------------
def handle_message(update):
    try:
        message = update.get("message", {})
        chat_id = message["chat"]["id"]
        text = message.get("text")
        photos = message.get("photo")

        if text == "/start":
            send_main_menu(chat_id)
            return

        elif text == "🎭 استیکرساز":
            api.send_message(chat_id, "📸 لطفاً عکس خود را ارسال کنید تا استیکر ساخته شود.")
            return

        elif text == "🤖 هوش مصنوعی":
            api.send_message(chat_id, "🧠 متن یا دستور خود را برای ساخت استیکر هوش مصنوعی ارسال کنید.")
            return

        elif photos:
            # وقتی عکس فرستاده میشه
            handle_sticker_upload(chat_id, photos[-1]["file_id"])
            return

        elif text:
            # وقتی متن فرستاده میشه برای هوش مصنوعی
            result = generate_sticker(text, chat_id)
            api.send_message(chat_id, result)
            return

        else:
            api.send_message(chat_id, "❌ متوجه نشدم، لطفاً یکی از گزینه‌های منو یا دستور معتبر بفرستید.")

    except Exception as e:
        logger.error(f"❌ خطا در handle_message: {e}")
