
from utils.logger import logger
from services import legacy as legacy_services

api = legacy_services.api
menu_manager = legacy_services.menu_manager
subscription_manager = legacy_services.subscription_manager
sticker_manager = legacy_services.sticker_manager

def handle_message(msg):
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text", "")
    logger.info("handle_message %s: %s", chat_id, text)

    if text == "/start":
        api.send_message(chat_id, "سلام! به ربات استیکرساز خوش آمدید.", reply_markup=menu_manager.main_keyboard_markup())
        return

    if text == "🎭 استیکرساز":
        api.send_message(chat_id, "لطفا عکس بفرستید تا استیکرش ساخته شود.")
        return

    if "photo" in msg or msg.get("document"):
        api.send_message(chat_id, "عکس دریافت شد، در حال پردازش...")
        sticker_manager.create_sticker_from_file(chat_id, "uploaded_file_path.jpg")
        return

    api.send_message(chat_id, "متوجه نشدم. از منوی اصلی استفاده کنید.", reply_markup=menu_manager.main_keyboard_markup())
