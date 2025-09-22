# handlers/messages.py
import logging
from config import BOT_TOKEN, CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# منوی اصلی (reply keyboard)
def send_main_menu(chat_id):
    text = "سلام 👋\nبه ربات خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:"
    reply_markup = {
        "keyboard": [
            ["🎭 استیکرساز", "🤖 هوش مصنوعی"],
            ["⭐ اشتراک", "🎁 تست رایگان"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    api.send_message(chat_id, text, reply_markup=reply_markup)

def handle_message(message: dict):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "").strip() if message.get("text") else ""

    logger.info(f"📩 handle_message {user_id}: {text}")

    # --- force join check ---
    try:
        in_channel = api.is_user_in_channel(CHANNEL_USERNAME, user_id)
    except Exception as e:
        logger.error(f"❌ خطا در بررسی عضویت: {e}")
        in_channel = False

    if not in_channel:
        # send inline keyboard with join link + check button (callback)
        reply_markup = {
            "inline_keyboard": [
                [{"text": "📢 عضویت در کانال", "url": f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"}],
                [{"text": "✅ بررسی مجدد", "callback_data": "check_membership"}]
            ]
        }
        api.send_message(chat_id,
                         f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n{CHANNEL_USERNAME}\n\nپس از عضویت روی «بررسی مجدد» بزنید.",
                         reply_markup=reply_markup)
        return

    # --- now user is allowed ---
    if text == "/start":
        send_main_menu(chat_id)
        return

    if text == "🎭 استیکرساز":
        # start sticker flow — minimal for now: ask pack name
        reply_markup = {"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}
        api.send_message(chat_id, "📦 نام پک استیکر خود را وارد کنید:", reply_markup=reply_markup)
        # NOTE: you should call your StickerManager.start_sticker_flow(user_id) here
        # if you have it: sticker_manager.start_sticker_flow(user_id)
        return

    if text == "🤖 هوش مصنوعی":
        reply_markup = {"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}
        api.send_message(chat_id, "🤖 متن یا دستور طراحی را وارد کنید:", reply_markup=reply_markup)
        # NOTE: start AI flow if you have ai_manager
        return

    if text == "⬅️ بازگشت":
        send_main_menu(chat_id)
        return

    # fallback
    api.send_message(chat_id, "متوجه نشدم، لطفا از منوی اصلی یکی از گزینه‌ها را انتخاب کنید.", reply_markup={
        "keyboard": [["🎭 استیکرساز", "🤖 هوش مصنوعی"], ["⭐ اشتراک"]], "resize_keyboard": True
    })
