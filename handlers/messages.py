import logging
from services import legacy as legacy_services

logger = logging.getLogger(__name__)


def handle_message(msg):
    user_id = msg["from"]["id"]
    text = msg.get("text", "")

    logger.info(f"handle_message {user_id}: {text}")

    # --- هندل دکمه‌ها ---
    if text == "🎭 استیکرساز":
        legacy_services.api.send_message(user_id, "لطفاً عکس بفرستید تا استیکرش ساخته شود.")
        return

    if text == "⭐ اشتراک":
        legacy_services.api.send_message(user_id, "برای خرید اشتراک، به وبسایت مراجعه کنید.")
        return

    if text == "🎁 تست رایگان":
        legacy_services.api.send_message(user_id, "شما یک روز تست رایگان دریافت کردید ✅")
        return

    # --- هندل عکس ---
    if "photo" in msg:
        photo = msg["photo"][-1]  # بزرگ‌ترین سایز
        file_id = photo["file_id"]

        legacy_services.sticker_manager.create_sticker_from_photo(user_id, file_id)
        return

    # --- پیش‌فرض ---
    legacy_services.api.send_message(user_id, "متوجه نشدم. از منوی اصلی استفاده کنید.")


def handle_callback(callback_query):
    user_id = callback_query["from"]["id"]
    data = callback_query["data"]

    logger.info(f"handle_callback {user_id}: {data}")

    if data == "menu_main":
        legacy_services.menu_manager.send_main_menu(user_id)
    elif data == "menu_sticker":
        legacy_services.api.send_message(user_id, "لطفاً عکس بفرستید تا استیکرش ساخته شود.")
    else:
        legacy_services.api.answer_callback_query(callback_query["id"], "گزینه نامعتبر است.")
