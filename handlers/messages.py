# handlers/messages.py

import logging
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI
from services.sticker_manager import handle_sticker_upload
from services.ai_manager import generate_sticker
from services.setting_manager import get_user_settings

api = TelegramAPI(BOT_TOKEN)
logger = logging.getLogger(__name__)


# 📌 منوی اصلی
def get_main_menu():
    return {
        "keyboard": [
            ["🎭 استیکرساز", "🤖 هوش مصنوعی"],
            ["⚙️ تنظیمات"]
        ],
        "resize_keyboard": True
    }


# 📌 هندل پیام‌ها
def handle_message(message, api_instance=None):
    user_id = message["from"]["id"]
    text = message.get("text", "")
    photo = message.get("photo")

    logger.info(f"📩 handle_message {user_id}: {text if text else '[PHOTO]'}")

    # ✅ استارت
    if text == "/start":
        api.send_message(
            user_id,
            "سلام 👋\nبه ربات خوش اومدی!\nلطفاً یکی از گزینه‌های زیر رو انتخاب کن:",
            reply_markup=get_main_menu()
        )
        return

    # ✅ استیکرساز
    if text == "🎭 استیکرساز":
        api.send_message(user_id, "لطفاً عکس مورد نظر برای ساخت استیکر رو ارسال کنید 📸")
        return

    # ✅ هوش مصنوعی
    if text == "🤖 هوش مصنوعی":
        api.send_message(user_id, "متن یا توضیحت رو بفرست تا برات استیکر خفن بسازم ✨")
        return

    # ✅ تنظیمات
    if text == "⚙️ تنظیمات":
        settings = get_user_settings(user_id)
        api.send_message(user_id, f"🔧 تنظیمات فعلی شما:\n{settings}")
        return

    # ✅ اگر عکس فرستاد → بفرست سمت استیکر منیجر
    if photo:
        handle_sticker_upload(user_id, photo, api)
        return

    # ✅ اگر متن معمولی فرستاد → بده به AI Manager
    if text:
        result = generate_sticker(text, user_id)
        api.send_message(user_id, result)
        return

    # fallback
    api.send_message(user_id, "متوجه نشدم 😅 لطفاً از منو استفاده کنید.")
