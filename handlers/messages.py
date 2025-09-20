# handlers/messages.py
import logging
from services import legacy as legacy_services

logger = logging.getLogger(__name__)
api = legacy_services.api
menu_manager = legacy_services.menu_manager
sticker_manager = legacy_services.sticker_manager
ai_manager = legacy_services.ai_manager
subscription_manager = legacy_services.subscription_manager

BACK_TEXT = "⬅️ بازگشت"

def handle_message(msg: dict):
    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    logger.info(f"📩 handle_message {user_id}: {text}")

    # 1) اگر کاربر دکمه بازگشت زد — اول این را چک کنیم
    if text == BACK_TEXT:
        # اگر توی استیکرساز بودیم، کنسلش کن
        if sticker_manager.is_in_sticker_flow(user_id):
            sticker_manager.cancel_flow(user_id)
        # اگر در AI بود
        elif ai_manager.is_in_ai_flow(user_id):
            ai_manager.cancel_flow(user_id)
        # اگر در subscription بود
        else:
            menu_manager.show_main_menu(user_id)
        return

    # 2) عکس
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        if sticker_manager.is_in_sticker_flow(user_id):
            sticker_manager.process_sticker_photo(user_id, file_id)
            return
        if ai_manager.is_in_ai_flow(user_id):
            ai_manager.process_ai_photo(user_id, file_id)
            return
        api.send_message(user_id, "لطفاً ابتدا یک گزینه از منوی اصلی انتخاب کنید.", reply_markup=menu_manager.main_menu())
        return

    # 3) متن (دستور/مراحل)
    if text:
        # شروع استیکرساز
        if text == "🎭 استیکرساز":
            sticker_manager.start_sticker_flow(user_id)
            api.send_message(user_id, "✍️ لطفاً نام پک استیکر را وارد کنید:", reply_markup=menu_manager.back_button())
            return

        # اگر در مرحله نام پک هست
        if sticker_manager.is_in_sticker_flow(user_id):
            # در حالت ما اسم پک باید ذخیره بشه
            session = sticker_manager.user_sessions.get(user_id, {})
            if session.get("step") == "pack_name":
                sticker_manager.set_pack_name(user_id, text)
                return
            if session.get("step") == "text":
                sticker_manager.add_text_to_sticker(user_id, text)
                return

        # شروع هوش مصنوعی
        if text == "🤖 هوش مصنوعی":
            ai_manager.start_ai_flow(user_id)
            api.send_message(user_id, "🤖 لطفاً عکس یا دستور طراحی را ارسال کنید.", reply_markup=menu_manager.back_button())
            return

        # اشتراک
        if text == "⭐ اشتراک":
            subscription_manager.show_subscription_menu(user_id)
            return

        if text == "🎁 تست رایگان":
            api.send_message(user_id, "🎉 تست رایگان فعال شد.", reply_markup=menu_manager.back_button())
            return

        # سایر متن‌ها (اگر در subscription باشیم باید handle کنیم)
        if subscription_manager and hasattr(subscription_manager, "handle_subscription_action"):
            subscription_manager.handle_subscription_action(user_id, text)
            return

        api.send_message(user_id, "متوجه نشدم. از منوی اصلی استفاده کنید.", reply_markup=menu_manager.main_menu())
        return

    # در هر حالت دیگر
    api.send_message(user_id, "فقط متن یا عکس ارسال کنید.", reply_markup=menu_manager.main_menu())
