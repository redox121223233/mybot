# mybot/handlers/messages.py  (ورژن پیشنهادی)
from utils.logger import logger
from services import legacy as legacy_services

api = legacy_services.api
menu_manager = legacy_services.menu_manager
subscription_manager = legacy_services.subscription_manager
sticker_manager = legacy_services.sticker_manager

# نگهداری state ساده در حافظه (در پروژهٔ نهایی بهتر توی DB)
user_state = {}  # chat_id -> {"mode":"ai","awaiting":"image" or "instructions","tmp_image":"/path/..."}

def handle_message(msg):
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text", "")
    logger.info("handle_message %s: %s", chat_id, text)

    state = user_state.get(chat_id, {})

    # شروع حالت AI
    if text == "🤖 استیکر هوش مصنوعی":
        user_state[chat_id] = {"mode":"ai", "awaiting":"image"}
        api.send_message(chat_id, "حالت استیکر هوش مصنوعی فعال شد. لطفاً یک تصویر بفرستید.")
        return

    # اگر در حالت ai و انتظار عکس داریم
    if state.get("mode") == "ai" and state.get("awaiting") == "image":
        # ذخیرهٔ فایل: در این نمونه فرض می‌کنیم فایل قبلاً دانلود و path را داریم.
        # در کد واقعی باید file_id را گرفته، با getFile و دانلود ذخیره کنی.
        # اینجا برای سادگی از document یا photo بررسی می‌کنیم:
        file_path = None
       if "photo" in msg:
    # photo list has different sizes, pick the biggest
    file_id = msg["photo"][-1]["file_id"]
    file_path = api.get_file(file_id, save_dir="/app/data/tmp")
elif msg.get("document"):
    file_id = msg["document"]["file_id"]
    file_path = api.get_file(file_id, save_dir="/app/data/tmp")

        # ذخیرهٔ مسیر موقت در state و درخواست دستورالعمل
        state["tmp_image"] = file_path
        state["awaiting"] = "instructions"
        user_state[chat_id] = state
        api.send_message(chat_id, "حالا دستور طراحی‌ت رو بنویس — مثلاً:\nمتن: سلام\nموقعیت: top-right\nرنگ: yellow\nفونت: arial\nاندازه: 48\nbold: yes")
        return

    # اگر در حالت ai و انتظار دستورالعمل داریم
    if state.get("mode") == "ai" and state.get("awaiting") == "instructions":
        instructions = text
        input_image = state.get("tmp_image")
        if not input_image:
            api.send_message(chat_id, "خطا: فایل تصویری پیدا نشد. دوباره تصویر را ارسال کنید.")
            user_state.pop(chat_id, None)
            return
        # call sticker_manager.create_ai_sticker
        sticker_manager.create_ai_sticker(chat_id, input_image, instructions)
        # clear state
        user_state.pop(chat_id, None)
        return

    # سایر حالات (منوی معمول)
    if text == "/start":
        api.send_message(chat_id, "سلام! به ربات خوش آمدید.", reply_markup=menu_manager.main_keyboard_markup())
        return

    # fallback
    api.send_message(chat_id, "متوجه نشدم. از منوی اصلی استفاده کنید.", reply_markup=menu_manager.main_keyboard_markup())
