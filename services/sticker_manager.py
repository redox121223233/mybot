import os
import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN, DATA_DIR

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# مسیر ذخیره استیکرهای موقت
STICKERS_DIR = os.path.join(DATA_DIR, "stickers")
os.makedirs(STICKERS_DIR, exist_ok=True)

# وضعیت کاربران
user_states = {}

def start_sticker_flow(user_id, chat_id):
    user_states[user_id] = {"step": "pack_name"}
    api.send_message(chat_id, "📝 لطفاً یک اسم برای پکیج استیکرت وارد کن:")

def handle_sticker_upload(message):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    text = message.get("text")
    photo = message.get("photo")

    state = user_states.get(user_id, {})

    # مرحله گرفتن اسم پک
    if state.get("step") == "pack_name" and text:
        state["pack_name"] = text.strip()
        state["step"] = "await_photo"
        api.send_message(chat_id, "📷 حالا یک عکس بفرست تا استیکر بسازیم:")
        return

    # مرحله گرفتن عکس
    if state.get("step") == "await_photo" and photo:
        file_id = photo[-1]["file_id"]
        dest_path = os.path.join(STICKERS_DIR, f"{user_id}.png")
        api.download_file(file_id, dest_path)
        state["photo"] = dest_path
        state["step"] = "await_text"
        api.send_message(chat_id, "✍️ متن مورد نظرت برای استیکر رو بفرست:")
        return

    # مرحله گرفتن متن
    if state.get("step") == "await_text" and text:
        state["text"] = text.strip()
        state["step"] = "build"
        build_sticker(user_id, chat_id)
        return

    api.send_message(chat_id, "❌ متوجه نشدم! لطفاً طبق مراحل پیش برو.")

def build_sticker(user_id, chat_id):
    state = user_states.get(user_id, {})
    pack_name = state.get("pack_name")
    photo = state.get("photo")
    text = state.get("text")

    if not (pack_name and photo and text):
        api.send_message(chat_id, "⚠️ اطلاعات ناقصه! از اول شروع کن.")
        return

    try:
        # اینجا باید پردازش تصویر/متن انجام بشه (در صورت نیاز با PIL یا OpenCV)
        api.send_sticker(chat_id, photo)
        api.send_message(chat_id, f"✅ استیکر ساخته شد!\n📦 پک: {pack_name}\n📝 متن: {text}")
    except Exception as e:
        logger.error(f"❌ خطا در ساخت استیکر: {e}")
        api.send_message(chat_id, "❌ خطایی رخ داد هنگام ساخت استیکر.")

    user_states.pop(user_id, None)
