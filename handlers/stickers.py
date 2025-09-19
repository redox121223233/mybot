from utils.logger import logger
from services import sticker_maker
from utils.telegram_api import send_message

def handle_sticker_message(chat_id, msg, ai_mode=False, design_opts=None):
    """وقتی کاربر عکسی می‌فرسته برای ساخت استیکر"""
    try:
        if "photo" not in msg:
            send_message(chat_id, "📷 لطفاً یک عکس بفرستید تا استیکر بسازم.")
            return "no_photo"

        # گرفتن بزرگ‌ترین سایز عکس
        photo = msg["photo"][-1]
        file_id = photo["file_id"]

        sticker_maker.create_sticker_from_file(chat_id, file_id, ai_mode, design_opts)

        send_message(chat_id, "✅ استیکر ساخته شد و به بسته‌ت اضافه شد.")
        return "ok"

    except Exception as e:
        logger.error(f"Error in handle_sticker_message: {e}")
        send_message(chat_id, "❌ خطا در ساخت استیکر")
        return "error"
