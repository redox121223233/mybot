
from utils.logger import logger
from services.database_manager import DatabaseManager
from utils.telegram_api import TelegramAPI

class StickerManager:
    def __init__(self, api: TelegramAPI, db: DatabaseManager, data_dir=None):
        self.api = api
        self.db = db
        self.data_dir = data_dir or db.base_dir

    def create_sticker_from_file(self, chat_id, file_path, pack_name=None):
        logger.info("create_sticker_from_file: %s -> pack=%s", file_path, pack_name)
        self.api.send_message(chat_id, "تصویر دریافت شد — در حال ساخت استیکر (پیاده‌سازی بعدی).")
