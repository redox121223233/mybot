# mybot/services/sticker_manager.py
import os
from utils.logger import logger
from services.database_manager import DatabaseManager
from utils.telegram_api import TelegramAPI
from services.ai_manager import render_text_on_image  # استفاده مستقیم از تابع

class StickerManager:
    def __init__(self, api: TelegramAPI, db: DatabaseManager, data_dir=None):
        self.api = api
        self.db = db
        self.data_dir = data_dir or db.base_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def create_sticker_from_file(self, chat_id, file_path, pack_name=None):
        # این متد placeholder است؛ اگر کاری بخواهد انجام شود اینجا پیاده بشود.
        logger.info("create_sticker_from_file: %s -> pack=%s", file_path, pack_name)
        self.api.send_message(chat_id, "تصویر دریافت شد — در حال ساخت استیکر (پیاده‌سازی بعدی).")

    def create_ai_sticker(self, chat_id, input_image_path, instructions_text, out_name=None):
        """
        Apply AIManager.render_text_on_image and send resulting image as a sticker/file.
        """
        # ensure out dir
        out_name = out_name or f"ai_sticker_{chat_id}.webp"
        out_path = os.path.join(self.data_dir, out_name)

        # call renderer
        try:
            render_text_on_image(input_image_path, out_path, instructions_text)
        except Exception as e:
            logger.exception("AI render failed: %s", e)
            self.api.send_message(chat_id, "خطا در پردازش تصویر رخ داد.")
            return

        # send file back to user (as a document — you can implement sendSticker via Bot API)
        # We'll use sendMessage with an attachment via sendDocument (not implemented in TelegramAPI wrapper)
        # Fallback: send as photo is complex; for now send message acknowledging and provide path (you replace with actual upload)
        self.api.send_message(chat_id, "استیکر ساخته شد. (پیاده‌سازی آپلود استیکر به تلگرام الزامی است)")
        # TODO: implement upload: sendDocument or createNewStickerSet + addStickerToSet
