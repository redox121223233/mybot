import logging
import os
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN, DATA_DIR

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)


def handle_sticker_upload(message, user_id, pack_name, text=None):
    """
    گرفتن عکس کاربر و ساختن/اضافه کردن استیکر به پک
    :param message: آپدیت تلگرام شامل photo
    :param user_id: آی‌دی کاربر
    :param pack_name: نام پک استیکر (یونیک)
    :param text: متن استیکر (اختیاری)
    """

    try:
        # ✅ گرفتن بزرگ‌ترین سایز عکس
        photos = message.get("photo")
        if not photos:
            logger.error("❌ هیچ عکسی پیدا نشد.")
            return False

        file_id = photos[-1]["file_id"]  # بزرگ‌ترین سایز
        logger.info(f"⬆️ دریافت عکس برای استیکر: user_id={user_id}, file_id={file_id}")

        # ✅ دانلود فایل
        dest_path = os.path.join(DATA_DIR, f"{user_id}_sticker.png")
        api.download_file(file_id, dest_path)

        # ✅ اسم پک باید یکتا باشه و به _by_bot ختم بشه
        # توجه: bot_username باید واقعی باشه (username رباتت)
        bot_username = "matnsticker_bot"
        full_pack_name = f"{pack_name}_by_{bot_username}"

        # ✅ بررسی وجود پک
        if not api.sticker_set_exists(full_pack_name):
            logger.info(f"📦 ساخت پک جدید: {full_pack_name}")
            api.create_new_sticker_set(
                user_id=user_id,
                name=full_pack_name,
                title=f"Sticker Pack by {user_id}",
                png_path=dest_path,
                emoji="😀"
            )
        else:
            logger.info(f"➕ افزودن استیکر جدید به پک: {full_pack_name}")
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
