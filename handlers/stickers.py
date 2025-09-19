from utils.telegram_api import send_message
from utils.logger import logger
from services.ai import apply_template

def handle_sticker_input(chat_id, file_id, file_type):
    try:
        send_message(chat_id, f"📥 فایل {file_type} دریافت شد. در حال پردازش...")
        # For now, if default template exists, apply it
        try:
            out = apply_template("default", "متن نمونه")
            send_message(chat_id, f"✅ پردازش انجام شد. فایل خروجی: {out}")
        except Exception as e:
            logger.error("Template apply failed: %s", e)
            send_message(chat_id, f"خطا در پردازش: {e}")
    except Exception as e:
        logger.error("Error in stickers.handle_sticker_input: %s", e)
        send_message(chat_id, "⚠️ خطا در پردازش فایل.")
