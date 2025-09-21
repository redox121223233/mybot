import logging
from config import BOT_TOKEN, CHANNEL_LINK
from utils.telegram_api import TelegramAPI
from services import legacy as legacy_services

logger = logging.getLogger(__name__)

api = TelegramAPI(BOT_TOKEN)
menu_manager = legacy_services.menu_manager
sticker_manager = legacy_services.sticker_manager
ai_manager = legacy_services.ai_manager
subscription_manager = legacy_services.subscription_manager


def handle_message(msg: dict):
    """مدیریت پیام‌های دریافتی از کاربر"""
    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    logger.info(f"📩 handle_message {user_id}: {text}")

    # --------- عضویت اجباری ---------
    if not api.is_user_in_channel(user_id, CHANNEL_LINK):
        api.send_message(
            user_id,
            "🚨 برای استفاده از ربات باید عضو کانال بشی:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📢 عضویت در کانال", "url": f"https://t.me/{CHANNEL_LINK.replace('@', '')}"}],
                    [{"text": "🔄 چک مجدد", "callback_data": "check_membership"}]
                ]
            }
        )
        return

    # --------- دستورات ---------
    if text == "/start":
        legacy_services.menu_manager.show_main_menu(user_id)

    elif text == "🎭 استیکرساز":
        api.send_message(user_id, "📦 لطفاً نام پک استیکر خود را وارد کنید ✍️",
                         reply_markup=menu_manager.back_button())
        sticker_manager.start_sticker_flow(user_id)

    elif text == "⭐ اشتراک":
        subscription_manager.show_subscription_menu(user_id)

    elif text == "🤖 هوش مصنوعی":
        api.send_message(user_id, "متن یا دستور طراحی خود را وارد کنید 🧠",
                         reply_markup=menu_manager.back_button())
        ai_manager.start_ai_flow(user_id)

    elif text == "⬅️ بازگشت":
        menu_manager.show_main_menu(user_id)

    elif "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        if sticker_manager.is_in_sticker_flow(user_id):
            sticker_manager.process_sticker_photo(user_id, file_id)
        elif ai_manager.is_in_ai_flow(user_id):
            ai_manager.process_ai_photo(user_id, file_id)
        else:
            api.send_message(user_id, "📌 از منوی اصلی یکی از گزینه‌ها را انتخاب کنید.",
                             reply_markup=menu_manager.main_menu())

    else:
        api.send_message(user_id, "❓ متوجه نشدم. از منوی اصلی استفاده کنید.",
                         reply_markup=menu_manager.main_menu())
