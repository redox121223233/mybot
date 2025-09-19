# mybot/services/sticker_manager.py
import os
from services.ai_manager import AIManager
from utils.logger import logger


class StickerManager:
    """
    مدیریت استیکرها:
    - دریافت عکس
    - اضافه کردن متن با هوش مصنوعی داخلی (AIManager)
    - ارسال خروجی به کاربر
    """

    def __init__(self, api, ai_manager=None):
        self.api = api
        self.ai = ai_manager or AIManager()
        self.output_dir = "/app/data/stickers"
        os.makedirs(self.output_dir, exist_ok=True)

    def create_sticker(self, chat_id, image_path, text=None, options=None):
        """
        ساخت استیکر با متن دلخواه.
        - image_path: مسیر عکس ورودی
        - text: متن (اختیاری)
        - options: دیکشنری تنظیمات (مثلاً {"position": "top", "color": "red"})
        """
        try:
            out_path = os.path.join(self.output_dir, f"{chat_id}_sticker.png")

            if text:
                logger.info("StickerManager: متن روی عکس اعمال می‌شود → %s", text)
                result = self.ai.apply_text(image_path, out_path, text, options)
            else:
                logger.info("StickerManager: فقط عکس بدون متن ارسال می‌شود")
                os.system(f"cp '{image_path}' '{out_path}'")
                result = out_path

            if result:
                self.api.send_photo(chat_id, result, caption="✅ استیکر آماده شد")
                return result
            else:
                self.api.send_message(chat_id, "❌ ساخت استیکر شکست خورد.")
                return None

        except Exception as e:
            logger.exception("StickerManager.create_sticker failed: %s", e)
            self.api.send_message(chat_id, "❌ خطای غیرمنتظره در ساخت استیکر.")
            return None
