import logging
import os
import requests
from config import BOT_TOKEN, DATA_DIR

logger = logging.getLogger(__name__)

# مسیر موقت برای استیکرها
STICKER_DIR = os.path.join(DATA_DIR, "stickers")
os.makedirs(STICKER_DIR, exist_ok=True)

def handle_sticker_upload(api, chat_id, file_id, user_id):
    """
    مدیریت آپلود عکس برای ساخت استیکر
    """
    try:
        logger.info(f"⬆️ دریافت عکس برای استیکر: user={user_id}, file_id={file_id}")

        # دریافت لینک فایل
        file_info = api.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['file_path']}"

        # دانلود فایل
        response = requests.get(file_url)
        if response.status_code != 200:
            logger.error("❌ دانلود فایل ناموفق: %s", response.text)
            return None

        # ذخیره موقت
        output_path = os.path.join(STICKER_DIR, f"sticker_{user_id}.png")
        with open(output_path, "wb") as f:
            f.write(response.content)

        logger.info(f"✅ فایل ذخیره شد: {output_path}")
        return output_path

    except Exception as e:
        logger.error("❌ خطا در آپلود استیکر", exc_info=True)
        return None
