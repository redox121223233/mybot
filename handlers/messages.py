import logging
from services import legacy as legacy_services

logger = logging.getLogger(__name__)
api = legacy_services.api
menu_manager = legacy_services.menu_manager
sticker_manager = legacy_services.sticker_manager
ai_manager = legacy_services.ai_manager
subscription_manager = legacy_services.subscription_manager


def handle_message(msg: dict):
    """مدیریت پیام‌های دریافتی از کاربر"""
    user_id = msg["from"]["id"]
    text = msg.get("text", "")
    logger.info(f"handle_message {user_id}: {text}")

    # اگر متن باشه
    if text:
        # شروع استیکرساز
        if text == "🎭 استیکرساز":
            api.send_message(user_id, "لطفاً نام پک استیکر خود را وارد کنید ✍️", reply_markup=menu_manager.back_button())
            sticker_manager.start_sticker_flow(user_id)

        # شروع اشتراک
        elif text == "⭐ اشتراک":
            api.send_message(user_id, "اینجا می‌تونی اشتراک بخری یا وضعیت خودتو ببینی 🌟", reply_markup=menu_manager.back_button())
            subscription_manager.show_subscription_menu(user_id)

        # تست رایگان
        elif text == "🎁 تست رایگان":
            api.send_message(user_id, "شما یک تست رایگان فعال دارید! 🎉", reply_markup=menu_manager.back_button())

        # شروع هوش مصنوعی
        elif text == "🤖 هوش مصنوعی":
            api.send_message(user_id, "متن یا دستور طراحی خود را وارد کنید (مثلاً: «عکس من با متن بالا سمت راست قرمز بولد») 🤖", reply_markup=menu_manager.back_button())
            ai_manager.start_ai_flow(user_id)

        # بازگشت
        elif text == "⬅️ بازگشت":
            menu_manager.show_main_menu(user_id)

        # ادامه استیکرساز
        elif sticker_manager.is_in_sticker_flow(user_id):
            sticker_manager.process_sticker_step(user_id, text=text)

        # ادامه هوش مصنوعی
        elif ai_manager.is_in_ai_flow(user_id):
            ai_manager.process_ai_step(user_id, text=text)

        # متن ناشناخته
        else:
            api.send_message(user_id, "متوجه نشدم. از منوی اصلی استفاده کنید.", reply_markup=menu_manager.main_menu())

    # اگر عکس باشه
    elif "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]

        if sticker_manager.is_in_sticker_flow(user_id):
            sticker_manager.process_sticker_step(user_id, file_id=file_id)

        elif ai_manager.is_in_ai_flow(user_id):
            ai_manager.process_ai_photo(user_id, file_id)

        else:
            api.send_message(user_id, "لطفاً از منوی اصلی یکی از گزینه‌ها را انتخاب کنید.", reply_markup=menu_manager.main_menu())

    else:
        api.send_message(user_id, "فقط متن یا عکس ارسال کنید.", reply_markup=menu_manager.main_menu())
