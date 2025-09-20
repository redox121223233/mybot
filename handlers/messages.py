import logging
from services import legacy as legacy_services

logger = logging.getLogger(__name__)
api = legacy_services.api
menu_manager = legacy_services.menu_manager
sticker_manager = legacy_services.sticker_manager
ai_manager = legacy_services.ai_manager
subscription_manager = legacy_services.subscription_manager

# وضعیت کاربران
user_states = {}

def set_state(user_id, state):
    user_states[user_id] = state
    logger.info(f"✅ تغییر وضعیت کاربر {user_id} → {state}")

def get_state(user_id):
    return user_states.get(user_id, "main_menu")


def handle_message(msg: dict):
    """مدیریت پیام‌های دریافتی"""
    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    logger.info(f"📩 handle_message {user_id}: {text}")

    state = get_state(user_id)

    # --- عکس دریافت شد ---
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]

        if state == "sticker_photo":
            sticker_manager.process_sticker_photo(user_id, file_id)
            set_state(user_id, "sticker_text")
            api.send_message(user_id, "📝 حالا متن استیکر رو وارد کنید:", reply_markup=menu_manager.back_button())

        elif state == "ai_flow":
            ai_manager.process_ai_photo(user_id, file_id)

        else:
            api.send_message(user_id, "📌 لطفاً اول یک گزینه از منوی اصلی انتخاب کنید.", reply_markup=menu_manager.main_menu())
        return

    # --- متن دریافت شد ---
    if text:
        # مرحله انتخاب اسم پک
        if state == "sticker_pack_name":
            sticker_manager.set_pack_name(user_id, text)
            set_state(user_id, "sticker_photo")
            api.send_message(user_id, "📷 حالا عکس رو بفرست تا استیکر ساخته بشه:", reply_markup=menu_manager.back_button())
            return

        # مرحله نوشتن متن استیکر
        elif state == "sticker_text":
            sticker_manager.add_text_to_sticker(user_id, text)
            set_state(user_id, "main_menu")
            api.send_message(user_id, "✅ استیکر ساخته شد!", reply_markup=menu_manager.main_menu())
            return

        # منوی اصلی
        if text == "🎭 استیکرساز":
            set_state(user_id, "sticker_pack_name")
            api.send_message(user_id, "✍️ لطفاً اسم پک استیکر خود را وارد کنید:", reply_markup=menu_manager.back_button())

        elif text == "⭐ اشتراک":
            set_state(user_id, "subscription_menu")
            subscription_manager.show_subscription_menu(user_id)

        elif text == "🎁 تست رایگان":
            set_state(user_id, "main_menu")
            api.send_message(user_id, "🎉 شما یک تست رایگان فعال دارید!", reply_markup=menu_manager.back_button())

        elif text == "🤖 هوش مصنوعی":
            set_state(user_id, "ai_flow")
            api.send_message(user_id, "🤖 متن یا دستور طراحی خود را بفرستید:", reply_markup=menu_manager.back_button())

        elif text == "⬅️ بازگشت":
            set_state(user_id, "main_menu")
            menu_manager.show_main_menu(user_id)

        else:
            if state == "subscription_menu":
                subscription_manager.handle_subscription_action(user_id, text)
            elif state == "ai_flow":
                ai_manager.process_ai_text(user_id, text)
            else:
                api.send_message(user_id, "❌ متوجه نشدم. از منوی اصلی استفاده کنید.", reply_markup=menu_manager.main_menu())
