import os
import logging
from PIL import Image, ImageDraw, ImageFont
from services.ai_manager import AIManager


class StickerManager:
    def __init__(self, api, db_manager, base_dir="."):
        """
        مدیریت ساخت استیکرها
        :param api: کلاس TelegramAPI
        :param db_manager: کلاس DatabaseManager
        :param base_dir: پوشه ذخیره‌سازی فایل‌ها
        """
        self.api = api
        self.db_manager = db_manager
        self.base_dir = base_dir
        self.ai = AIManager()

    def _get_font(self, font_size=40, font_path=None):
        """برگرداندن فونت"""
        try:
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, font_size)
            return ImageFont.truetype("arial.ttf", font_size)
        except:
            logging.warning("هیچ فونت استاندارد پیدا نشد. از پیش‌فرض PIL استفاده می‌شود.")
            return ImageFont.load_default()

    def create_sticker_from_photo(self, user_id, file_id, text=None, style=None):
        """
        📷 ساخت استیکر از عکس ارسالی کاربر
        :param user_id: شناسه کاربر
        :param file_id: شناسه فایل تلگرام
        :param text: متن دلخواه روی استیکر
        :param style: دیکشنری شامل رنگ، موقعیت، اندازه فونت
        """
        try:
            file_path = self.api.get_file(file_id)
            local_path = self.api.download_file(file_path)

            img = Image.open(local_path).convert("RGBA")
            draw = ImageDraw.Draw(img)

            if text:
                font = self._get_font(style.get("font_size", 40))
                color = style.get("color", "yellow")
                position = style.get("position", "bottom")

                w, h = draw.textsize(text, font=font)
                if position == "top":
                    pos = ((img.width - w) / 2, 10)
                elif position == "center":
                    pos = ((img.width - w) / 2, (img.height - h) / 2)
                else:  # bottom
                    pos = ((img.width - w) / 2, img.height - h - 10)

                draw.text(pos, text, font=font, fill=color)

            sticker_path = os.path.join(self.base_dir, f"sticker_{user_id}.png")
            img.save(sticker_path, "PNG")

            self.api.send_photo(user_id, sticker_path)
            logging.info(f"استیکر عکس برای کاربر {user_id} ساخته شد.")
            return True

        except Exception as e:
            logging.error(f"خطا در ساخت استیکر از عکس: {e}")
            self.api.send_message(user_id, "❌ مشکلی در ساخت استیکر پیش آمد.")
            return False

    def create_sticker_from_text(self, user_id, text, style=None):
        """
        📝 ساخت استیکر فقط از متن
        """
        try:
            img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            font = self._get_font(style.get("font_size", 60))
            color = style.get("color", "black")
            w, h = draw.textsize(text, font=font)

            pos = ((512 - w) / 2, (512 - h) / 2)
            draw.text(pos, text, font=font, fill=color)

            sticker_path = os.path.join(self.base_dir, f"text_sticker_{user_id}.png")
            img.save(sticker_path, "PNG")

            self.api.send_photo(user_id, sticker_path)
            logging.info(f"استیکر متن برای کاربر {user_id} ساخته شد.")
            return True

        except Exception as e:
            logging.error(f"خطا در ساخت استیکر متنی: {e}")
            self.api.send_message(user_id, "❌ مشکلی در ساخت استیکر متنی پیش آمد.")
            return False

    def create_ai_sticker(self, user_id, command):
        """
        🤖 استفاده از AIManager برای درک دستور کاربر
        مثال: "یه عکس بگیر روش بنویس سلام زرد بالای عکس"
        """
        try:
            ai_result = self.ai.process_command(command)

            if ai_result.get("mode") == "text":
                return self.create_sticker_from_text(
                    user_id,
                    ai_result.get("text"),
                    ai_result.get("style", {})
                )

            elif ai_result.get("mode") == "photo":
                file_id = ai_result.get("file_id")
                return self.create_sticker_from_photo(
                    user_id,
                    file_id,
                    ai_result.get("text"),
                    ai_result.get("style", {})
                )

            else:
                self.api.send_message(user_id, "🤖 دستور شما رو متوجه نشدم.")
                return False

        except Exception as e:
            logging.error(f"خطا در استیکر هوش مصنوعی: {e}")
            self.api.send_message(user_id, "❌ مشکلی در پردازش دستور پیش آمد.")
            return False
