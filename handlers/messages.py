import logging
import os
from config import CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI
from service.ai_manager import generate_sticker   # تغییر مسیر
from service.sticker_manager import update_user_settings, reset_user_settings  # تغییر مسیر

api = TelegramAPI()
logger = logging.getLogger(__name__)

def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "🎭 استیکرساز"}],
            [{"text": "🤖 هوش مصنوعی"}],
            [{"text": "⚙️ تنظیمات استیکر"}, {"text": "♻️ ریست تنظیمات"}]
        ],
        "resize_keyboard": True
    }
    api.send_message(chat_id, "📍 یکی از گزینه‌ها را انتخاب کنید:", reply_markup=keyboard)

def handle_message(message):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    text = message.get("text")
    photos = message.get("photo")

    logger.info(f"📩 handle_message {user_id}: {text or '📷 photo'}")

    # عضویت اجباری
    try:
        member = api.get_chat_member(CHANNEL_USERNAME, user_id)
        status = member["result"]["status"]
        if status not in ["member", "administrator", "creator"]:
            api.send_message(chat_id, f"📢 برای استفاده از ربات ابتدا عضو شوید:\n{CHANNEL_USERNAME}\nسپس /start را بزنید ✅")
            return
    except Exception as e:
        logger.error(f"❌ خطا در بررسی عضویت: {e}")
        return

    # شروع
    if text == "/start":
        send_main_menu(chat_id)

    elif text == "🎭 استیکرساز":
        api.send_message(chat_id, "📷 یک عکس ارسال کنید یا متنی بنویسید تا تبدیل به استیکر شود.")

    elif text == "🤖 هوش مصنوعی":
        api.send_message(chat_id, "✍️ متن خود را وارد کنید تا تبدیل به استیکر هوشمند شود.")

    elif text == "⚙️ تنظیمات استیکر":
        api.send_message(chat_id, "🎨 تنظیمات:\n1️⃣ رنگ متن\n2️⃣ اندازه فونت\n3️⃣ موقعیت متن")

    elif text == "♻️ ریست تنظیمات":
        reset_user_settings(user_id)
        api.send_message(chat_id, "✅ تنظیمات پیش‌فرض بازیابی شد.")

    elif photos:
        file_id = photos[-1]["file_id"]
        dest_path = f"/tmp/{user_id}_photo.png"
        api.download_file(file_id, dest_path)

        sticker_path = generate_sticker(user_id, "متن شما اینجاست", dest_path)
        if sticker_path:
            api.send_sticker(chat_id, sticker_path)
        else:
            api.send_message(chat_id, "❌ مشکلی در ساخت استیکر پیش آمد.")

    elif text:
        sticker_path = generate_sticker(user_id, text)
        if sticker_path:
            api.send_sticker(chat_id, sticker_path)
        else:
            api.send_message(chat_id, "❌ مشکلی در ساخت استیکر پیش آمد.")

    else:
        api.send_message(chat_id, "❌ متوجه نشدم، لطفاً دوباره تلاش کنید.")
