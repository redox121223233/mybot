import logging
from utils.telegram_api import TelegramAPI
from services.sticker_manager import (
    handle_sticker_upload,
    handle_text_choice,
    handle_text_input,
)

logger = logging.getLogger(__name__)
api = TelegramAPI()

# حافظه موقت وضعیت کاربرها
USER_STATE = {}  # {user_id: {"state": str, "pack": str, "photo": dict}}


def handle_message(update):
    try:
        message = update.get("message", {})
        user_id = message.get("from", {}).get("id")
        text = message.get("text")
        photos = message.get("photo")

        logger.info(f"📩 handle_message {user_id}: {text if text else '[photo]'}")

        # 📌 اگر کاربر /start زد
        if text == "/start":
            api.send_message(
                user_id,
                "👋 خوش آمدید!\nیکی از گزینه‌ها رو انتخاب کنید:",
                reply_markup={
                    "keyboard": [
                        [{"text": "🎭 استیکرساز"}],
                        [{"text": "🤖 هوش مصنوعی"}],
                        [{"text": "⚙️ تنظیمات"}],
                    ],
                    "resize_keyboard": True,
                },
            )
            USER_STATE[user_id] = {"state": "idle"}
            return

        # 📌 وقتی کاربر استیکرساز رو انتخاب می‌کنه
        if text == "🎭 استیکرساز":
            api.send_message(user_id, "📸 لطفاً یک عکس ارسال کنید تا به استیکر تبدیل بشه.")
            USER_STATE[user_id] = {"state": "awaiting_photo", "pack": f"pack_{user_id}"}
            return

        # 📌 دریافت عکس
        if photos and USER_STATE.get(user_id, {}).get("state") == "awaiting_photo":
            USER_STATE[user_id]["photo"] = update
            USER_STATE[user_id]["state"] = "awaiting_text_choice"

            api.send_message(
                user_id,
                "✍️ میخوای روی استیکرت متن هم بذارم؟",
                reply_markup={
                    "keyboard": [
                        [{"text": "بله ✍️"}],
                        [{"text": "خیر 🚫"}],
                    ],
                    "resize_keyboard": True,
                    "one_time_keyboard": True,
                },
            )
            return

        # 📌 انتخاب بله/خیر
        if USER_STATE.get(user_id, {}).get("state") == "awaiting_text_choice":
            result = handle_text_choice(USER_STATE[user_id]["photo"], user_id, USER_STATE[user_id]["pack"])
            if result == "awaiting_text":
                USER_STATE[user_id]["state"] = "awaiting_text"
            else:
                USER_STATE[user_id]["state"] = "idle"
            return

        # 📌 وقتی کاربر متن رو ارسال می‌کنه
        if USER_STATE.get(user_id, {}).get("state") == "awaiting_text":
            handle_text_input(USER_STATE[user_id]["photo"], user_id, USER_STATE[user_id]["pack"])
            USER_STATE[user_id]["state"] = "idle"
            return

    except Exception as e:
        logger.error(f"❌ Error handling update: {e}", exc_info=True)
