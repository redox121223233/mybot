from utils.telegram_api import send_message
from utils.logger import logger
from services.database import load_user_if_missing, set_user_mode, get_user_state
from services.subscription import handle_trial_activation, show_subscription_menu

def handle_message(msg):
    try:
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        if not chat_id:
            return "no chat_id"
        load_user_if_missing(chat_id)
        text = msg.get("text")
        if text:
            text = text.strip()
            if text.startswith("/"):
                if text == "/start":
                    send_message(chat_id, "👋 سلام! به ربات خوش آمدید.")
                    return "ok"
                if text.startswith("/admin"):
                    send_message(chat_id, "🔒 فرمان ادمین دریافت شد.")
                    return "ok"
                send_message(chat_id, "⚠️ دستور ناشناخته.")
                return "ok"
            if text in ["🎁 تست رایگان","🎁 دوره رایگان"]:
                handle_trial_activation(chat_id, msg.get("message_id"))
                return "ok"
            if text in ["⭐ اشتراک","💎 خرید اشتراک"]:
                show_subscription_menu(chat_id, msg.get("message_id"))
                return "ok"
            if text in ["🎭 استیکرساز"]:
                set_user_mode(chat_id, "sticker")
                send_message(chat_id, "🎭 استیکرساز فعال شد. لطفاً عکس یا متن بفرستید.")
                return "ok"
        # photos
        if "photo" in msg:
            photos = msg.get("photo", [])
            if photos:
                file_id = photos[-1].get("file_id")
                from handlers.stickers import handle_sticker_input
                handle_sticker_input(chat_id, file_id, "photo")
                return "ok"
        if "sticker" in msg:
            sticker = msg.get("sticker", {})
            file_id = sticker.get("file_id")
            from handlers.stickers import handle_sticker_input
            handle_sticker_input(chat_id, file_id, "sticker")
            return "ok"
        return "ok"
    except Exception as e:
        logger.error(f"Error in messages.handle_message: {e}")
        try:
            send_message(msg.get("chat",{}).get("id"), "⚠️ خطا در پردازش پیام.")
        except: pass
        return "ok"
