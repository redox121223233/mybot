import logging
from services.ai_manager import generate_sticker
from services.sticker_manager import handle_sticker_upload
from services.setting_manager import get_user_settings
from services.menu_manager import get_main_menu

logger = logging.getLogger(__name__)


def handle_message(update: dict, api):
    """
    هندل کردن پیام‌های کاربر
    """
    if not isinstance(update, dict):
        logger.error(f"❌ Update is not a dict: {type(update)}")
        return

    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    text = message.get("text")
    photos = message.get("photo")

    logger.info(f"📩 handle_message {user_id}: {text or '[photo]'}")

    # ================= دستورات =================
    if text == "/start":
        api.send_message(
            chat_id,
            "👋 خوش آمدید!\nیکی از گزینه‌ها رو انتخاب کنید:",
            reply_markup=get_main_menu()
        )

    elif text == "🎭 استیکرساز":
        api.send_message(chat_id, "📸 لطفاً یک عکس ارسال کنید تا به استیکر تبدیل بشه.")

    elif text == "🤖 هوش مصنوعی":
        api.send_message(chat_id, "📝 متن خودت رو بفرست تا تبدیل به استیکر بشه.")

    elif text:
        # کاربر متن داده → تولید استیکر هوش مصنوعی
        sticker = generate_sticker(text, user_id)
        api.send_message(chat_id, sticker)

    elif photos:
        # کاربر عکس داده → هندل استیکرساز
        handle_sticker_upload(api, chat_id, user_id, photos)

    else:
        api.send_message(chat_id, "❌ متوجه نشدم. از دکمه‌ها استفاده کن.")
