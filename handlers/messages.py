import logging
from config import CHANNEL_LINK
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
    logger.info(f"📩 handle_message {user_id}: {text}")

    # ==============================
    # 🔒 Force Join (عضویت اجباری)
    # ==============================
    if not api.is_user_in_channel(user_id, CHANNEL_LINK):
        if text == "🔄 چک عضویت":
            if api.is_user_in_channel(user_id, CHANNEL_LINK):
                menu_manager.show_main_menu(user_id)
            else:
                api.send_message(
                    user_id,
                    f"📢 برای استفاده از ربات باید عضو کانال بشی:\n{CHANNEL_LINK}",
                    reply_markup={"keyboard": [["🔄 چک عضویت"]], "resize_keyboard": True}
                )
        else:
            api.send_message(
                user_id,
                f"📢 برای استفاده از ربات باید عضو کانال بشی:\n{CHANNEL_LINK}",
                reply_markup={"keyboard": [["🔄 چک عضویت"]], "resize_keyboard": True}
            )
        return

    # ==============================
    # 🎯 منو اصلی
    # ==============================
    if text:
        if text == "/start":
            # ریست همه‌ی فلـوها
            sticker_manager.cancel_flow(user_id)
            ai_manager.cancel_flow(user_id)
            subscription_manager.cancel_flow(user_id)
            menu_manager.show_main_menu(user_id)

        elif text == "🎭 استیکرساز":
            api.send_message(user_id, "📦 لطفاً نام پک استیکر خود را وارد کنید ✍️")
            sticker_manager.start_sticker_flow(user_id)

        elif text == "⭐ اشتراک":
            subscription_manager.show_subscription_menu(user_id)

        elif text == "🎁 تست رایگان":
            api.send_message(user_id, "🎉 شما یک تست رایگان فعال دارید!")

        elif text == "🤖 هوش مصنوعی":
            api.send_message(user_id, "✍️ متن یا دستور طراحی خود را وارد کنید:")
            ai_manager.start_ai_flow(user_id)

        elif text == "⬅️ بازگشت":
            # ریست همه‌ی فلـوها
            sticker_manager.cancel_flow(user_id)
            ai_manager.cancel_flow(user_id)
            subscription_manager.cancel_flow(user_id)
            menu_manager.show_main_menu(user_id)

        else:
            # ==============================
            # 🎭 داخل فلو استیکرساز
            # ==============================
            if sticker_manager.is_in_sticker_flow(user_id):
                flow = sticker_manager.user_flows[user_id]
                step = flow.get("step")

                if step == "pack_name":
                    sticker_manager.set_pack_name(user_id, text)

                elif step == "text":
                    sticker_manager.add_text_to_sticker(user_id, text)

                return

            # ==============================
            # 🤖 داخل فلو هوش مصنوعی
            # ==============================
            if ai_manager.is_in_ai_flow(user_id):
                ai_manager.process_ai_text(user_id, text)
                return

            # ==============================
            # ❌ متن ناشناس
            # ==============================
            api.send_message(user_id, "❓ متوجه نشدم. از منو اصلی استفاده کنید.", reply_markup=menu_manager.main_menu())

    # ==============================
    # 📷 اگر عکس فرستاد
    # ==============================
    elif "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]

        if sticker_manager.is_in_sticker_flow(user_id):
            sticker_manager.process_sticker_photo(user_id, file_id)

        elif ai_manager.is_in_ai_flow(user_id):
            ai_manager.process_ai_photo(user_id, file_id)

        else:
            api.send_message(user_id, "📌 لطفاً اول از منو یک گزینه انتخاب کنید.", reply_markup=menu_manager.main_menu())

    else:
        api.send_message(user_id, "📌 فقط متن یا عکس ارسال کنید.", reply_markup=menu_manager.main_menu())
