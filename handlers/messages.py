import logging
from services import legacy as legacy_services

logger = logging.getLogger(__name__)
api = legacy_services.api
menu_manager = legacy_services.menu_manager
sticker_manager = legacy_services.sticker_manager
ai_manager = legacy_services.ai_manager
subscription_manager = legacy_services.subscription_manager

def handle_message(msg: dict):
    user_id = msg["from"]["id"]
    text = msg.get("text", "")

    logger.info(f"📩 handle_message {user_id}: {text}")

    # دستور /start
    if text == "/start":
        sticker_manager.cancel_flow(user_id)
        ai_manager.cancel_flow(user_id)
        if hasattr(subscription_manager, "cancel_flow"):
            subscription_manager.cancel_flow(user_id)
        menu_manager.show_main_menu(user_id)
        return

    # متن‌ها
    if text:
        if text == "🎭 استیکرساز":
            sticker_manager.start_sticker_flow(user_id)
        elif text == "⭐ اشتراک":
            subscription_manager.show_subscription_menu(user_id)
        elif text == "🎁 تست رایگان":
            api.send_message(user_id, "شما یک تست رایگان فعال دارید 🎉", reply_markup=menu_manager.back_button())
        elif text == "🤖 هوش مصنوعی":
            ai_manager.start_ai_flow(user_id)
        elif text == "⬅️ بازگشت":
            menu_manager.show_main_menu(user_id)
        else:
            if sticker_manager.is_in_sticker_flow(user_id):
                flow = sticker_manager.user_flows[user_id]
                if flow["step"] == "pack_name":
                    sticker_manager.set_pack_name(user_id, text)
                elif flow["step"] == "text":
                    sticker_manager.add_text_to_sticker(user_id, text)
            elif ai_manager.is_in_ai_flow(user_id):
                ai_manager.process_ai_text(user_id, text)
            else:
                api.send_message(user_id, "متوجه نشدم. از منو استفاده کنید.", reply_markup=menu_manager.main_menu())
    elif "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        if sticker_manager.is_in_sticker_flow(user_id):
            sticker_manager.process_sticker_photo(user_id, file_id)
        elif ai_manager.is_in_ai_flow(user_id):
            ai_manager.process_ai_photo(user_id, file_id)
        else:
            api.send_message(user_id, "لطفاً از منو استفاده کنید.", reply_markup=menu_manager.main_menu())
    else:
        api.send_message(user_id, "فقط متن یا عکس بفرستید.", reply_markup=menu_manager.main_menu())
