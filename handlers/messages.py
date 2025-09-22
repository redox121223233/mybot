# handlers/messages.py
import logging
from config import CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN
from services.sticker_manager import handle_sticker_upload
from services.ai_manager import generate_sticker

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# ------------------ ارسال منوی اصلی ------------------
def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "🎭 استیکرساز"}],
            [{"text": "🤖 هوش مصنوعی"}],
        ],
        "resize_keyboard": True
    }
    api.send_message(chat_id, "✨ به ربات خوش آمدید!\nیکی از گزینه‌ها را انتخاب کنید:", reply_markup=keyboard)

# ------------------ مدیریت پیام ------------------
def handle_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")
    photo = message.get("photo")

    logger.info(f"📩 handle_message {user_id}: {text}")

    try:
        # ------------------ دستور /start ------------------
        if text == "/start":
            send_main_menu(chat_id)
            return

        # ------------------ استیکرساز ------------------
        if text == "🎭 استیکرساز":
            api.send_message(chat_id, "📸 لطفاً یک عکس بفرستید تا استیکر بسازم!")
            return

        # اگر عکس ارسال شد → استیکرساز
        if photo:
            file_id = photo[-1]["file_id"]  # بزرگ‌ترین سایز عکس
            handle_sticker_upload(chat_id, file_id, user_id)
            return

        # ------------------ هوش مصنوعی ------------------
        if text == "🤖 هوش مصنوعی":
            api.send_message(chat_id, "🧠 یک متن بفرست تا تبدیل به استیکر کنم!")
            return

        # اگر کاربر متن عادی فرستاد → تبدیل به استیکر با هوش مصنوعی
        if text:
            sticker = generate_sticker(text, user_id)
            api.send_message(chat_id, f"✨ {sticker}")
            return

        # ------------------ حالت پیش‌فرض ------------------
        api.send_message(chat_id, "❓ متوجه نشدم، لطفاً از منو یکی رو انتخاب کن.")

    except Exception as e:
        logger.error(f"❌ Error in handle_message: {e}")
        api.send_message(chat_id, "❌ خطایی رخ داد، دوباره امتحان کنید.")
