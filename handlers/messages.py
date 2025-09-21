import logging
from config import BOT_TOKEN, CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI
from services.ai_manager import AIManager
from services.sticker_manager import StickerManager

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)
ai_manager = AIManager(api)
sticker_manager = StickerManager(api)

# ------------------ کیبورد اصلی ------------------
MAIN_KB = {
    "keyboard": [["🎭 استیکرساز"], ["🤖 هوش مصنوعی"]],
    "resize_keyboard": True
}

AI_KB = {
    "keyboard": [
        ["✍️ متن جدید", "🎨 رنگ متن"],
        ["📍 موقعیت متن", "🔤 فونت"],
        ["🔄 ریست تنظیمات", "⬅️ بازگشت"]
    ],
    "resize_keyboard": True
}

def send_main_menu(user_id):
    api.send_message(user_id, "📌 یکی از گزینه‌ها را انتخاب کنید:", reply_markup=MAIN_KB)

# ------------------ پیام‌ها ------------------
def handle_message(msg):
    user_id = msg["from"]["id"]
    text = msg.get("text", "")

    logger.info(f"📩 handle_message {user_id}: {text}")

    # عضویت اجباری
    if not api.is_user_in_channel(CHANNEL_USERNAME, user_id):
        api.send_message(user_id, f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n{CHANNEL_USERNAME}\n\nسپس /start را بزنید ✅")
        return

    # دستورات اصلی
    if text == "/start":
        send_main_menu(user_id)

    elif text == "🎭 استیکرساز":
        sticker_manager.start_flow(user_id)

    elif text == "🤖 هوش مصنوعی":
        api.send_message(user_id, "⚙️ تنظیمات هوش مصنوعی:", reply_markup=AI_KB)

    elif text == "⬅️ بازگشت":
        send_main_menu(user_id)

    elif text == "🔄 ریست تنظیمات":
        ai_manager.reset_settings(user_id)
        api.send_message(user_id, "✅ تنظیمات ریست شد.", reply_markup=AI_KB)

    else:
        # اگر در جریان استیکرساز هست
        flow = sticker_manager.user_flows.get(user_id)
        if flow:
            step = flow["step"]
            if step == "pack_name":
                sticker_manager.set_pack_name(user_id, text)
            elif step == "text":
                sticker_manager.add_text_and_build(user_id, text)
        else:
            api.send_message(user_id, "❌ متوجه نشدم. لطفاً از منو استفاده کنید.", reply_markup=MAIN_KB)
