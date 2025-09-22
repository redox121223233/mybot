# services/sticker_manager.py
import os
import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN, DATA_DIR

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

STICKERS_DIR = os.path.join(DATA_DIR, "stickers")
os.makedirs(STICKERS_DIR, exist_ok=True)

def handle_sticker_upload(chat_id, file_id, user_id=None):
    """
    📸 دریافت عکس کاربر و ساخت استیکر ساده
    :param chat_id: چت مقصد
    :param file_id: file_id عکس ارسال‌شده توسط کاربر
    :param user_id: (اختیاری) شناسه کاربر
    """
    try:
        # مسیر ذخیره‌سازی عکس
        photo_path = os.path.join(STICKERS_DIR, f"{file_id}.jpg")

        # دانلود فایل از تلگرام
        api.download_file(file_id, photo_path)

        # شبیه‌سازی تبدیل به استیکر (اینجا میشه AI یا PIL اضافه کرد)
        logger.info(f"🎨 استیکر ساخته شد برای {chat_id} از {photo_path}")

        # ارسال به کاربر
        api.send_sticker(chat_id, photo_path)

        return True

    except Exception as e:
        logger.error(f"❌ خطا در handle_sticker_upload: {e}")
        api.send_message(chat_id, "❌ خطا در ساخت استیکر. دوباره تلاش کنید.")
        return False
