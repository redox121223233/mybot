import logging
from utils.telegram_api import TelegramAPI
from services.sticker_manager import handle_sticker_upload

logger = logging.getLogger(__name__)
api = TelegramAPI()


def handle_message(update):
    try:
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_id = message.get("from", {}).get("id")
        text = message.get("text")

        logger.info(f"📩 handle_message {user_id}: {text}")

        if text == "/start":
            keyboard = {
                "keyboard": [
                    [{"text": "🎭 استیکرساز"}],
                    [{"text": "🤖 هوش مصنوعی"}],
                    [{"text": "⚙️ تنظیمات"}],
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }

            api.send_message(
                chat_id,
                "👋 خوش آمدید!\nیکی از گزینه‌ها رو انتخاب کنید:",
                reply_markup=keyboard   # ❌ نه json.dumps → همون dict
            )

        elif text == "🎭 استیکرساز":
            api.send_message(chat_id, "📸 لطفاً یک عکس ارسال کنید تا به استیکر تبدیل بشه.")

        elif "photo" in message:
            photos = message.get("photo")
            if photos:
                pack_name = f"pack_{user_id}"
                success = handle_sticker_upload(update, user_id, pack_name)
                if success:
                    api.send_message(chat_id, "✅ استیکر ساخته شد!")
                else:
                    api.send_message(chat_id, "❌ خطا در ساخت استیکر. دوباره تلاش کنید.")

        else:
            api.send_message(chat_id, "❓ گزینه نامعتبر. لطفاً یکی از دکمه‌ها رو انتخاب کنید.")

    except Exception as e:
        logger.error(f"❌ Error handling update: {e}", exc_info=True)
