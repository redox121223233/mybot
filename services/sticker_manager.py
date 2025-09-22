import os
import logging
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI

logger = logging.getLogger(__name__)

# ✅ نمونه API
api = TelegramAPI(BOT_TOKEN)
DATA_DIR = "/tmp"


def handle_sticker_upload(update: dict, user_id: int, pack_name: str, text: str = None):
    """
    گرفتن عکس کاربر و ساختن/اضافه کردن استیکر به پک
    :param update: dict آپدیت تلگرام
    :param user_id: آی‌دی کاربر
    :param pack_name: نام پک
    :param text: متن استیکر (اختیاری)
    """
    try:
        # ✅ مطمئن میشیم که update یک دیکشنری هست
        if not isinstance(update, dict):
            logger.error(f"❌ update دیکشنری نیست: {type(update)}")
            return False

        message = update.get("message", {})
        photos = message.get("photo")
        if not photos:
            logger.error("❌ هیچ عکسی پیدا نشد.")
            return False

        # ✅ گرفتن بزرگ‌ترین سایز عکس
        file_id = photos[-1]["file_id"]
        logger.info(f"⬆️ دریافت عکس برای استیکر: user_id={user_id}, file_id={file_id}")

        # ✅ دانلود فایل
        dest_path = os.path.join(DATA_DIR, f"{user_id}_sticker.png")
        api.download_file(file_id, dest_path)

        bot_username = "matnsticker_bot"
        full_pack_name = f"{pack_name}_by_{bot_username}"

        # ✅ ساخت یا اضافه کردن استیکر
        if not api.sticker_set_exists(full_pack_name):
            api.create_new_sticker_set(
                user_id=user_id,
                name=full_pack_name,
                title=f"Sticker Pack by {user_id}",
                png_path=dest_path,
                emoji="😀"
            )
        else:
            api.add_sticker_to_set(
                user_id=user_id,
                name=full_pack_name,
                png_path=dest_path,
                emoji="😀"
            )

        logger.info("✅ استیکر با موفقیت ساخته/اضافه شد.")
        return True

    except Exception as e:
        logger.error(f"❌ خطا در آپلود استیکر: {e}", exc_info=True)
        return False


def reset_user_settings(user_id: int):
    """
    ریست کردن تنظیمات کاربر (مثلاً وقتی از نو شروع کنه)
    """
    try:
        settings_path = os.path.join(DATA_DIR, f"{user_id}_settings.json")
        if os.path.exists(settings_path):
            os.remove(settings_path)
            logger.info(f"🔄 تنظیمات کاربر {user_id} ریست شد.")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در ریست تنظیمات کاربر {user_id}: {e}", exc_info=True)
        return False
