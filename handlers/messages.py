from services.sticker_manager import handle_sticker_upload, handle_text_choice, handle_text_input
from utils.telegram_api import TelegramAPI
import os

api = TelegramAPI(token=os.getenv("BOT_TOKEN"))

# مدیریت مرحله‌ها برای هر کاربر
user_states = {}

def handle_message(update):
    message = update.get("message", {})
    user_id = message["from"]["id"]
    text = message.get("text")
    photos = message.get("photo")

    # 1️⃣ اگه عکس فرستاد → برو مرحله انتخاب متن
    if photos:
        handle_sticker_upload(update, user_id, pack_name="custompack")
        user_states[user_id] = "waiting_for_text_choice"
        return

    # 2️⃣ اگه منتظر انتخاب متن بودیم
    if user_states.get(user_id) == "waiting_for_text_choice":
        if text in ["بله ✍️", "خیر 🚀"]:
            handle_text_choice(user_id, text)
            if text == "بله ✍️":
                user_states[user_id] = "waiting_for_text_input"
            else:
                user_states.pop(user_id, None)
        else:
            api.send_message(user_id, "فقط بله ✍️ یا خیر 🚀 رو انتخاب کن.")
        return

    # 3️⃣ اگه منتظر متن بودیم
    if user_states.get(user_id) == "waiting_for_text_input":
        if text:
            handle_text_input(user_id, text)
            user_states.pop(user_id, None)
        else:
            api.send_message(user_id, "✍️ یه متن بفرست.")
        return

    # شروع اولیه
    if text == "/start":
        api.send_message(user_id, "👋 خوش آمدی! یک گزینه انتخاب کن:", reply_markup={
            "keyboard": [[{"text": "🎭 استیکرساز"}], [{"text": "🤖 هوش مصنوعی"}]],
            "resize_keyboard": True
        })
        return

    if text == "🎭 استیکرساز":
        api.send_message(user_id, "📸 لطفاً یک عکس ارسال کن تا استیکر بسازم.")
        user_states[user_id] = "waiting_for_photo"
        return

    api.send_message(user_id, "متوجه نشدم، یکی از گزینه‌ها رو بفرست.")

