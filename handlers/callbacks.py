import logging
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI
from handlers.messages import send_main_menu, user_states, user_settings

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# ------------------ هندلر کال‌بک ------------------
def handle_callback(callback_query):
    user_id = callback_query["from"]["id"]
    data = callback_query["data"]

    logger.info(f"🔘 handle_callback {user_id}: {data}")

    # استارت دوباره منو
    if data == "main_menu":
        user_states[user_id] = "main_menu"
        send_main_menu(user_id)

    # تغییر رنگ متن
    elif data.startswith("set_color_"):
        color = data.split("_", 2)[2]
        user_settings[user_id]["color"] = color
        api.send_message(user_id, f"✅ رنگ متن روی {color} تنظیم شد")

    # تغییر فونت
    elif data.startswith("set_font_"):
        font = data.split("_", 2)[2]
        user_settings[user_id]["font"] = f"fonts/{font}.ttf"
        api.send_message(user_id, f"✅ فونت تغییر کرد ({font})")

    # تغییر موقعیت متن
    elif data.startswith("set_pos_"):
        pos = data.split("_", 2)[2]
        user_settings[user_id]["position"] = pos
        api.send_message(user_id, f"✅ متن در موقعیت {pos} قرار گرفت")

    # ریست تنظیمات
    elif data == "reset_settings":
        user_settings[user_id] = {
            "font": "fonts/default.ttf",
            "color": "white",
            "position": "bottom"
        }
        api.send_message(user_id, "♻️ تنظیمات ریست شد")

    else:
        api.send_message(user_id, "❌ این دکمه ناشناخته است")
