import logging
from config import CHANNEL_LINK
from services import legacy as legacy_services

logger = logging.getLogger(__name__)

api = legacy_services.api
menu_manager = legacy_services.menu_manager
sticker_manager = legacy_services.sticker_manager
ai_manager = legacy_services.ai_manager
subscription_manager = legacy_services.subscription_manager

# ================= منوها ==================
main_menu = {
    "keyboard": [
        ["🎭 استیکرساز", "🤖 هوش مصنوعی"],
        ["⭐ اشتراک", "🎁 تست رایگان"]
    ],
    "resize_keyboard": True
}

back_button = {
    "keyboard": [["⬅️ بازگشت"]],
    "resize_keyboard": True
}

# ================= مدیریت پیام‌ها ==================
def handle_message(msg: dict):
    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    logger.info(f"📩 handle_message {user_id}: {text}")

    # بررسی عضویت اجباری
    try:
        if not api.is_user_in_channel(user_id, CHANNEL_LINK):
            api.send_message(
                user_id,
                f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n{CHANNEL_LINK}",
                reply_markup=main_menu
            )
            return
    except Exception as e:
        logger.error(f"❌ خطا در بررسی عضویت: {e}")
        return

    # ================= دستورات =================
    if text == "/start":
        sticker_manager.cancel_flow(user_id)
        ai_manager.cancel_flow(user_id)
        api.send_message(user_id, "به منوی اصلی خوش اومدی 🌟", reply_markup=main_menu)

    elif text == "🎭 استیکرساز":
        api.send_message(user_id, "📦 لطفاً نام پک استیکر خود را وارد کنید:", reply_markup=back_button)
        sticker_manager.start_sticker_flow(user_id)

    elif text == "🤖 هوش مصنوعی":
        api.send_message(user_id, "✍️ متن یا دستور طراحی خود را وارد کنید:", reply_markup=back_button)
        ai_manager.start_ai_flow(user_id)

    elif text == "⭐ اشتراک":
        subscription_manager.show_subscription_menu(user_id)

    elif text == "🎁 تست رایگان":
        api.send_message(user_id, "🎉 شما یک تست رایگان فعال دارید!", reply_markup=back_button)

    elif text == "⬅️ بازگشت":
        sticker_manager.cancel_flow(user_id)
        ai_manager.cancel_flow(user_id)
        api.send_message(user_id, "↩️ بازگشت به منوی اصلی", reply_markup=main_menu)

    # ================= استیکر ساز =================
    elif sticker_manager.is_in_sticker_flow(user_id):
        flow = sticker_manager.user_flows[user_id]
        if flow["step"] == "pack_name":
            sticker_manager.set_pack_name(user_id, text)
        elif flow["step"] == "text":
            sticker_manager.add_text_to_sticker(user_id, text)

    # ================= هوش مصنوعی =================
    elif ai_manager.is_in_ai_flow(user_id):
        ai_manager.process_ai_text(user_id, text)

    # ================= دریافت عکس =================
    elif "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        if sticker_manager.is_in_sticker_flow(user_id):
            sticker_manager.process_sticker_photo(user_id, file_id)
        elif ai_manager.is_in_ai_flow(user_id):
            ai_manager.process_ai_photo(user_id, file_id)
        else:
            api.send_message(user_id, "❌ لطفاً یکی از گزینه‌های منو را انتخاب کنید.", reply_markup=main_menu)

    else:
        api.send_message(user_id, "متوجه نشدم! از منوی اصلی استفاده کنید.", reply_markup=main_menu)
