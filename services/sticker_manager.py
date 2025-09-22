import logging
import os
from config import DATA_DIR
from utils.settings_manager import get_user_settings

logger = logging.getLogger(__name__)

def handle_sticker_upload(api, chat_id, photos):
    largest_photo = photos[-1]
    file_id = largest_photo["file_id"]
    dest_path = os.path.join(DATA_DIR, f"{chat_id}_sticker.jpg")

    try:
        api.download_file(file_id, dest_path)
        settings = get_user_settings(chat_id)
        logger.info(f"🎭 Sticker created with settings {settings}")
        api.send_sticker(chat_id, dest_path)
    except Exception as e:
        logger.error(f"❌ خطا در ساخت استیکر: {e}")
        api.send_message(chat_id, "❌ خطا در ساخت استیکر.")
