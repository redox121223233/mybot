from utils.logger import logger
try:
    from services import legacy
    process_fn = getattr(legacy, "process_message", None) or getattr(legacy, "handle_message", None)
except Exception:
    legacy = None
    process_fn = None

def process_message(message):
    if process_fn:
        try:
            return process_fn(message)
        except Exception as e:
            logger.error("Error in legacy process_message: %s", e)
            # fallback minimal behavior
    # fallback minimal implementation
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = message.get("text")
    if text == "/start":
        # simple welcome
        try:
from utils.telegram_api import send_message, edit_message_text
            send_message(chat_id, "👋 سلام! ربات آماده است.")
        except:
            pass
    return "ok"