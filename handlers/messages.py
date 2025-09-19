# handlers/messages.py
from utils.telegram_api import send_message, edit_message_text
from utils.logger import logger

def process_message(msg):
    """پردازش پیام‌های دریافتی"""
    try:
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id:
            return "no chat_id"

        if "text" in msg:
            text = msg["text"]

            # دستور /start
            if text.startswith("/start"):
                send_message(chat_id, "سلام 👋 به ربات استیکرساز خوش اومدی!")
                return "ok"

            # دستور /admin
            elif text.startswith("/admin"):
                send_message(chat_id, "بخش مدیریت فعال شد ⚙️")
                return "ok"

            # دکمه‌های منو
            elif text == "🎭 استیکرساز":
                send_message(chat_id, "📷 لطفاً عکس‌تون رو بفرستید تا تبدیل به استیکر بشه.")
                return "ok"

            elif text == "🎁 تست رایگان":
                send_message(chat_id, "🎁 تست رایگان فعال شد!")
                return "ok"

            elif text == "⭐ اشتراک":
                send_message(chat_id, "⭐ برای خرید اشتراک به سایت مراجعه کنید.")
                return "ok"

        return "ok"

    except Exception as e:
        logger.error(f"Error in process_message: {e}")
        return "error"
