# handlers/messages.py
import logging
import os
from config import CHANNEL_USERNAME, DATA_DIR
from utils.telegram_api import TelegramAPI
from ai_manager import generate_sticker

logger = logging.getLogger(__name__)

api = TelegramAPI(os.getenv("BOT_TOKEN"))

# حافظه وضعیت کاربران
user_states = {}

def send_main_menu(chat_id):
    """ارسال منوی اصلی"""
    keyboard = {
        "keyboard": [
            [{"text": "🎭 استیکرساز"}, {"text": "🤖 هوش مصنوعی"}],
            [{"text": "ℹ️ راهنما"}]
        ],
        "resize_keyboard": True
    }
    api.send_message(chat_id, "📍 یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=keyboard)


def handle_message(message):
    """مدیریت پیام‌های دریافتی"""
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    logger.info(f"📩 handle_message {user_id}: {text}")

    # --- عضویت اجباری ---
    try:
        if not api.is_user_in_channel(CHANNEL_USERNAME, user_id):
            join_text = (
                f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n"
                f"{CHANNEL_USERNAME}\n\n"
                "سپس /start را بزنید ✅"
            )
            api.send_message(chat_id, join_text)
            return
    except Exception as e:
        logger.error(f"❌ خطا در بررسی عضویت: {e}")
        api.send_message(chat_id, "⚠️ خطا در بررسی عضویت. دوباره تلاش کنید.")
        return

    # --- دستورات اصلی ---
    if text == "/start":
        user_states[user_id] = {"mode": "menu"}
        send_main_menu(chat_id)

    elif text == "🎭 استیکرساز":
        user_states[user_id] = {"mode": "sticker"}
        api.send_message(chat_id, "🖼 لطفاً یک عکس ارسال کنید تا استیکر ساخته شود.")

    elif text == "🤖 هوش مصنوعی":
        user_states[user_id] = {"mode": "ai_mode"}
        api.send_message(chat_id, "✍️ متن خود را بفرستید تا استیکر هوش مصنوعی ساخته شود.")

    elif text == "ℹ️ راهنما":
        api.send_message(chat_id,
            "📖 راهنما:\n\n"
            "🎭 استیکرساز → عکس بده، برات استیکر می‌سازم.\n"
            "🤖 هوش مصنوعی → متن بده، برات استیکر خوشگل می‌سازم.\n"
            "📌 حتما عضو کانال باش: " + CHANNEL_USERNAME
        )

    else:
        # --- حالت استیکرساز ---
        state = user_states.get(user_id, {}).get("mode")

        if state == "sticker" and "photo" in message:
            try:
                # بزرگترین سایز عکس
                photo = message["photo"][-1]
                file_id = photo["file_id"]

                dest_path = os.path.join(DATA_DIR, f"sticker_{user_id}.jpg")
                api.download_file(file_id, dest_path)

                api.send_sticker(chat_id, dest_path)
                api.send_message(chat_id, "✅ استیکر ساخته شد!")

                send_main_menu(chat_id)

            except Exception as e:
                logger.error(f"❌ خطا در ساخت استیکر: {e}")
                api.send_message(chat_id, "⚠️ خطا در ساخت استیکر!")

        # --- حالت هوش مصنوعی ---
        elif state == "ai_mode" and text:
            try:
                path = generate_sticker(text, user_id)
                api.send_sticker(chat_id, path)
                api.send_message(chat_id, "✅ استیکر هوش مصنوعی ساخته شد!")
                send_main_menu(chat_id)
            except Exception as e:
                logger.error(f"❌ خطا در ساخت استیکر هوش مصنوعی: {e}")
                api.send_message(chat_id, "⚠️ خطا در ساخت استیکر هوش مصنوعی!")

        else:
            api.send_message(chat_id, "🤔 متوجه نشدم. لطفاً از منو یکی از گزینه‌ها را انتخاب کنید.")
            send_main_menu(chat_id)
