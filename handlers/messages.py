import logging
import os
from config import CHANNEL_USERNAME, DATA_DIR, BOT_TOKEN
from utils.telegram_api import TelegramAPI
from ai_manager import generate_sticker

logger = logging.getLogger(__name__)

api = TelegramAPI(BOT_TOKEN)
user_states = {}

def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "🎭 استیکرساز"}, {"text": "🤖 هوش مصنوعی"}],
            [{"text": "ℹ️ راهنما"}]
        ],
        "resize_keyboard": True
    }
    api.send_message(chat_id, "📍 یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=keyboard)

def handle_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    logger.info(f"📩 handle_message {user_id}: {text}")

    # عضویت اجباری
    if not api.is_user_in_channel(CHANNEL_USERNAME, user_id):
        join_text = (
            f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n"
            f"{CHANNEL_USERNAME}\n\n"
            "سپس /start را بزنید ✅"
        )
        api.send_message(chat_id, join_text)
        return

    # دستورات
    if text == "/start":
        user_states[user_id] = {"mode": "menu"}
        send_main_menu(chat_id)

    elif text == "🎭 استیکرساز":
        user_states[user_id] = {"mode": "sticker"}
        api.send_message(chat_id, "🖼 لطفاً یک عکس ارسال کنید.")

    elif text == "🤖 هوش مصنوعی":
        user_states[user_id] = {"mode": "ai"}
        api.send_message(chat_id, "✍️ متن خود را بفرستید تا استیکر ساخته شود.")

    elif text == "ℹ️ راهنما":
        api.send_message(chat_id,
            "📖 راهنما:\n\n"
            "🎭 استیکرساز → عکس بده، استیکر بگیر.\n"
            "🤖 هوش مصنوعی → متن بده، استیکر بگیر.\n"
            "📌 عضو کانال شو: " + CHANNEL_USERNAME
        )

    else:
        state = user_states.get(user_id, {}).get("mode")

        if state == "sticker" and "photo" in message:
            try:
                photo = message["photo"][-1]
                file_id = photo["file_id"]
                dest = os.path.join(DATA_DIR, f"sticker_{user_id}.jpg")
                api.download_file(file_id, dest)
                api.send_sticker(chat_id, dest)
                api.send_message(chat_id, "✅ استیکر ساخته شد!")
                send_main_menu(chat_id)
            except Exception as e:
                logger.error(f"❌ خطا در استیکرساز: {e}")
                api.send_message(chat_id, "⚠️ خطا در ساخت استیکر!")

        elif state == "ai" and text:
            try:
                path = generate_sticker(text, user_id)
                api.send_sticker(chat_id, path)
                api.send_message(chat_id, "✅ استیکر هوش مصنوعی ساخته شد!")
                send_main_menu(chat_id)
            except Exception as e:
                logger.error(f"❌ خطا در AI: {e}")
                api.send_message(chat_id, "⚠️ خطا در استیکر هوش مصنوعی!")

        else:
            api.send_message(chat_id, "🤔 متوجه نشدم. از منو انتخاب کن.")
            send_main_menu(chat_id)
