import os
import logging
from PIL import Image, ImageDraw, ImageFont
from utils.telegram_api import TelegramAPI

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, api: TelegramAPI, base_dir: str = "/tmp"):
        self.api = api
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def create_sticker(self, file_id: str, text: str, pack_name: str) -> str:
        """
        ساخت استیکر از عکس + متن
        - file_id: آیدی فایل عکس تلگرام
        - text: متنی که روی استیکر نوشته بشه
        - pack_name: اسم پک (برای ذخیره مرتب در پوشه)
        """
        try:
            # دانلود عکس از تلگرام
            photo_path = os.path.join(self.base_dir, f"{file_id}.jpg")
            self.api.download_file(file_id, photo_path)
            logger.info(f"File downloaded for sticker: {photo_path}")

            # باز کردن عکس
            image = Image.open(photo_path).convert("RGBA")

            # کشیدن متن روی عکس
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("arial.ttf", 40)  # فونت اصلی
            except:
                logger.warning("هیچ فونت استاندارد پیدا نشد. از پیش‌فرض PIL استفاده می‌شود.")
                font = ImageFont.load_default()

            # متن وسط عکس
            text_width, text_height = draw.textsize(text, font=font)
            x = (image.width - text_width) // 2
            y = image.height - text_height - 20
            draw.text((x, y), text, font=font, fill="yellow")

            # پوشه پک
            pack_dir = os.path.join(self.base_dir, "stickers", pack_name)
            os.makedirs(pack_dir, exist_ok=True)

            # ذخیره استیکر
            sticker_path = os.path.join(pack_dir, f"{file_id}.png")
            image.save(sticker_path, "PNG")
            logger.info(f"Sticker created: {sticker_path}")

            return sticker_path

        except Exception as e:
            logger.error(f"خطا در ساخت استیکر: {e}")
            raise
