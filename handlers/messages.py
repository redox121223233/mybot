import logging
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# ------------------ وضعیت و تنظیمات ------------------
user_states = {}
user_settings = {}

def init_user(user_id):
    if user_id not in user_states:
        user_states[user_id] = "main_menu"
    if user_id not in user_settings:
        user_settings[user_id] = {
            "font": "fonts/default.ttf",
            "color": "white",
            "position": "bottom"
        }

# ------------------ کیبوردها ------------------
main_menu = {
    "keyboard": [
        ["🎭 استیکرساز", "🤖 هوش مصنوعی"],
        ["⭐ اشتراک", "🎁 تست رایگان"],
        ["ℹ️ راهنما"]
    ],
    "resize_keyboard": True
}

sticker_menu = {
    "keyboard": [
        ["📸 ارسال عکس", "✍️ نوشتن متن"],
        ["⬅️ بازگشت به منو"]
    ],
    "resize_keyboard": True
}

ai_menu = {
    "keyboard": [
        ["🎨 رنگ متن", "🔠 فونت"],
        ["📍 موقعیت متن", "🔄 ریست تنظیمات"],
        ["📝 شروع نوشتن", "⬅️ بازگشت به منو"]
    ],
    "resize_keyboard": True
}

# ------------------ منوی اصلی ------------------
def send_main_menu(chat_id):
    api.send_message(chat_id, "👋 به منوی اصلی خوش آمدید", reply_markup=main_menu)

# ------------------ هندلر پیام ------------------
def handle_message(message):
    user_id = message["from"]["id"]
    text = message.get("text", "")

    init_user(user_id)
    state = user_states[user_id]

    logger.info(f"📩 handle_message {user_id}: {text}")

    # ----- دستور start -----
    if text == "/start":
        user_states[user_id] = "main_menu"
        send_main_menu(user_id)
        return

    # ----- منوی اصلی -----
    if state == "main_menu":
        if text == "🎭 استیکرساز":
            user_states[user_id] = "sticker_waiting_photo"
            api.send_message(user_id, "📸 لطفاً یک عکس ارسال کنید", reply_markup=sticker_menu)

        elif text == "🤖 هوش مصنوعی":
            user_states[user_id] = "ai_settings"
            api.send_message(user_id, "⚙️ تنظیمات هوش مصنوعی:", reply_markup=ai_menu)

        else:
            api.send_message(user_id, "❌ گزینه نامعتبر است. یکی از دکمه‌ها را انتخاب کنید", reply_markup=main_menu)

    # ----- استیکرساز -----
    elif state == "sticker_waiting_photo":
        if "photo" in message:
            file_id = message["photo"][-1]["file_id"]
            logger.info(f"📷 عکس دریافت شد: {file_id}")
            user_states[user_id] = "sticker_waiting_text"
            api.send_message(user_id, "✍️ حالا متن مورد نظر را ارسال کنید")
        elif text == "⬅️ بازگشت به منو":
            user_states[user_id] = "main_menu"
            send_main_menu(user_id)
        else:
            api.send_message(user_id, "❌ لطفاً یک عکس ارسال کنید", reply_markup=sticker_menu)

    elif state == "sticker_waiting_text":
        if text == "⬅️ بازگشت به منو":
            user_states[user_id] = "main_menu"
            send_main_menu(user_id)
        else:
            api.send_message(user_id, f"✅ متن '{text}' روی عکس اعمال شد و استیکر ساخته شد")
            user_states[user_id] = "main_menu"
            send_main_menu(user_id)

    # ----- تنظیمات هوش مصنوعی -----
    elif state == "ai_settings":
        if text == "🎨 رنگ متن":
            user_settings[user_id]["color"] = "red"
            api.send_message(user_id, "✅ رنگ متن روی قرمز تنظیم شد")

        elif text == "🔠 فونت":
            user_settings[user_id]["font"] = "fonts/fancy.ttf"
            api.send_message(user_id, "✅ فونت تغییر کرد")

        elif text == "📍 موقعیت متن":
            user_settings[user_id]["position"] = "top"
            api.send_message(user_id, "✅ متن به بالای تصویر منتقل شد")

        elif text == "🔄 ریست تنظیمات":
            user_settings[user_id] = {
                "font": "fonts/default.ttf",
                "color": "white",
                "position": "bottom"
            }
            api.send_message(user_id, "♻️ تنظیمات ریست شد")

        elif text == "📝 شروع نوشتن":
            user_states[user_id] = "ai_waiting_text"
            api.send_message(user_id, "✍️ متن خود را ارسال کنید")

        elif text == "⬅️ بازگشت به منو":
            user_states[user_id] = "main_menu"
            send_main_menu(user_id)

        else:
            api.send_message(user_id, "❌ گزینه نامعتبر است", reply_markup=ai_menu)

    elif state == "ai_waiting_text":
        font = user_settings[user_id]["font"]
        color = user_settings[user_id]["color"]
        pos = user_settings[user_id]["position"]

        api.send_message(user_id, f"✅ متن '{text}' با تنظیمات فونت={font}, رنگ={color}, موقعیت={pos} اعمال شد")
        user_states[user_id] = "main_menu"
        send_main_menu(user_id)
