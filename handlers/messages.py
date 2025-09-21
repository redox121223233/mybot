import logging
from config import CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI
from services.sticker_manager import process_sticker

logger = logging.getLogger(__name__)
api = TelegramAPI("YOUR_BOT_TOKEN")  # 🔑 توکن واقعی اینجا

# ذخیره وضعیت کاربر
user_states = {}
user_settings = {}

# ------------------ منو اصلی ------------------
def send_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "🎭 استیکرساز"}],
            [{"text": "🤖 هوش مصنوعی (تنظیمات)"}],
            [{"text": "ℹ️ راهنما"}]
        ],
        "resize_keyboard": True
    }
    api.send_message(chat_id, "🏠 منو اصلی:", reply_markup=keyboard)

# ------------------ پیام‌ها ------------------
def handle_message(message):
    user_id = message["from"]["id"]
    text = message.get("text", "")
    chat_id = message["chat"]["id"]

    logger.info(f"📩 handle_message {user_id}: {text}")

    # بررسی عضویت
    if not api.is_user_in_channel(CHANNEL_USERNAME, user_id):
        api.send_message(chat_id, f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n@{CHANNEL_USERNAME}\n\nسپس /start را بزنید ✅")
        return

    # /start → منو اصلی
    if text == "/start":
        send_main_menu(chat_id)
        user_states[user_id] = None
        return

    # ------------------ استیکرساز ------------------
    if text == "🎭 استیکرساز":
        user_states[user_id] = "awaiting_photo"
        api.send_message(chat_id, "📷 لطفا عکست رو بفرست تا روش متن بچسبونم!")
        return

    if user_states.get(user_id) == "awaiting_photo" and "photo" in message:
        file_id = message["photo"][-1]["file_id"]
        photo_path = f"temp/photo_{user_id}.jpg"
        api.download_file(file_id, photo_path)

        user_settings.setdefault(user_id, {})
        user_settings[user_id]["last_photo"] = photo_path

        user_states[user_id] = "awaiting_text"
        api.send_message(chat_id, "📝 حالا متن دلخواهت رو بفرست!")
        return

    if user_states.get(user_id) == "awaiting_text" and text:
        photo_path = user_settings[user_id].get("last_photo")
        if not photo_path:
            api.send_message(chat_id, "❌ اول باید عکس بدی.")
        else:
            out_path = process_sticker(user_id, photo_path, text=text, settings=user_settings.get(user_id, {}))
            if out_path:
                api.send_sticker(chat_id, out_path)
                api.send_message(chat_id, "✅ استیکرت آماده شد!")
            else:
                api.send_message(chat_id, "❌ مشکلی در ساخت استیکر پیش آمد.")

        user_states[user_id] = None
        return

    # ------------------ تنظیمات هوش مصنوعی ------------------
    if text == "🤖 هوش مصنوعی (تنظیمات)":
        keyboard = {
            "keyboard": [
                [{"text": "🎨 تغییر رنگ متن"}, {"text": "🔠 تغییر فونت"}],
                [{"text": "🔝 موقعیت متن"}, {"text": "🔠 سایز متن"}],
                [{"text": "♻️ ریست تنظیمات"}],
                [{"text": "🔙 بازگشت"}]
            ],
            "resize_keyboard": True
        }
        api.send_message(chat_id, "⚙️ تنظیمات دلخواهت رو انتخاب کن:", reply_markup=keyboard)
        return

    if text == "🎨 تغییر رنگ متن":
        user_states[user_id] = "set_color"
        api.send_message(chat_id, "🎨 لطفا رنگ متن رو وارد کن (مثل: red یا #FF0000)")
        return

    if user_states.get(user_id) == "set_color" and text:
        user_settings.setdefault(user_id, {})
        user_settings[user_id]["color"] = text
        api.send_message(chat_id, "✅ رنگ متن ذخیره شد!")
        user_states[user_id] = None
        return

    if text == "🔠 تغییر فونت":
        user_states[user_id] = "set_font"
        api.send_message(chat_id, "🔠 اسم فونت رو وارد کن (مثلا: Arial.ttf)")
        return

    if user_states.get(user_id) == "set_font" and text:
        user_settings.setdefault(user_id, {})
        user_settings[user_id]["font"] = text
        api.send_message(chat_id, "✅ فونت ذخیره شد!")
        user_states[user_id] = None
        return

    if text == "🔝 موقعیت متن":
        user_states[user_id] = "set_position"
        api.send_message(chat_id, "📍 موقعیت رو وارد کن (top / center / bottom)")
        return

    if user_states.get(user_id) == "set_position" and text:
        user_settings.setdefault(user_id, {})
        user_settings[user_id]["position"] = text
        api.send_message(chat_id, "✅ موقعیت ذخیره شد!")
        user_states[user_id] = None
        return

    if text == "🔠 سایز متن":
        user_states[user_id] = "set_size"
        api.send_message(chat_id, "🔢 لطفا سایز متن رو وارد کن (مثل: 32)")
        return

    if user_states.get(user_id) == "set_size" and text.isdigit():
        user_settings.setdefault(user_id, {})
        user_settings[user_id]["size"] = int(text)
        api.send_message(chat_id, "✅ سایز ذخیره شد!")
        user_states[user_id] = None
        return

    if text == "♻️ ریست تنظیمات":
        user_settings[user_id] = {}
        api.send_message(chat_id, "♻️ تنظیمات به حالت پیش‌فرض برگشت.")
        return

    if text == "🔙 بازگشت":
        send_main_menu(chat_id)
        return

    # ------------------ راهنما ------------------
    if text == "ℹ️ راهنما":
        api.send_message(chat_id, "📖 راهنما:\n\n- 🎭 استیکرساز → عکس + متن بده، استیکر آماده میشه.\n- 🤖 تنظیمات → رنگ، فونت، موقعیت، سایز متن رو تغییر بده.\n- ♻️ ریست → تنظیماتت پاک میشه.\n- 🔙 بازگشت → برگشت به منو اصلی.")
        return

    # ------------------ پیش‌فرض ------------------
    api.send_message(chat_id, "❓ متوجه نشدم. لطفا از منو استفاده کن.")
