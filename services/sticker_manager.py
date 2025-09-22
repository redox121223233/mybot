# services/sticker_manager.py
import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

def handle_sticker_creation(chat_id, photo_file_id, user_id):
    """
    مدیریت فرایند استیکرسازی با عکس ارسال‌شده توسط کاربر
    """
    try:
        logger.info(f"📥 دریافت عکس از کاربر {user_id}, file_id={photo_file_id}")

        # دانلود فایل
        dest_path = f"data/downloads/{user_id}_input.jpg"
        api.download_file(photo_file_id, dest_path)

        # اینجا باید پردازش تصویر بشه (نوشتن متن روی عکس، فونت، رنگ و ...)
        # فعلاً شبیه‌سازی می‌کنیم
        result_path = f"data/stickers/{user_id}_sticker.png"

        # شبیه‌سازی خروجی
        with open(result_path, "wb") as f:
            f.write(b"FAKE_STICKER_CONTENT")

        logger.info(f"✅ استیکر ساخته شد: {result_path}")

        # ارسال استیکر
        api.send_sticker(chat_id, result_path)

    except Exception as e:
        logger.error(f"❌ خطا در ساخت استیکر: {e}")
        api.send_message(chat_id, "❌ خطا در ساخت استیکر! لطفاً دوباره امتحان کنید.")
