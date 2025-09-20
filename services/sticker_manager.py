import os
from PIL import Image, ImageDraw, ImageFont
import logging

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, api, base_dir="stickers"):
        self.api = api
        self.base_dir = base_dir
        self.user_sessions = {}  # ذخیره وضعیت هر کاربر
        os.makedirs(self.base_dir, exist_ok=True)

    def start_sticker_flow(self, user_id):
        """شروع فرآیند ساخت استیکر"""
        self.user_sessions[user_id] = {"step": "pack_name"}
        logger.info(f"🎭 کاربر {user_id} وارد حالت استیکرساز شد.")

    def set_pack_name(self, user_id, pack_name):
        """ذخیره اسم پک استیکر"""
        if user_id not in self.user_sessions:
            self.start_sticker_flow(user_id)
        self.user_sessions[user_id]["pack_name"] = pack_name
        self.user_sessions[user_id]["step"] = "photo"
        logger.info(f"📦 کاربر {user_id} نام پک انتخاب کرد: {pack_name}")

    def process_sticker_photo(self, user_id, file_id):
        """ذخیره عکس برای استیکر"""
        session = self.user_sessions.get(user_id, {})
        if not session:
            logger.warning(f"⚠️ کاربر {user_id} در حالت استیکرساز نبود.")
            return

        file_path = f"{self.base_dir}/{user_id}_sticker.jpg"
        self.api.download_file(file_id, file_path)
        session["photo"] = file_path
        session["step"] = "text"
        logger.info(f"📷 عکس استیکر ذخیره شد: {file_path}")

    def add_text_to_sticker(self, user_id, text):
        """اضافه کردن متن به عکس و ساخت استیکر"""
        session = self.user_sessions.get(user_id, {})
        if not session or "photo" not in session:
            logger.error(f"❌ عکس برای کاربر {user_id} یافت نشد.")
            return

        photo_path = session["photo"]
        output_path = f"{self.base_dir}/{user_id}_final.png"

        try:
            image = Image.open(photo_path).convert("RGBA")
            draw = ImageDraw.Draw(image)

            # فونت پیش‌فرض
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()

            # متن وسط بچسبه
            w, h = image.size
            text_w, text_h = draw.textsize(text, font=font)
            draw.text(((w - text_w) / 2, h - text_h - 10), text, fill="yellow", font=font)

            image.save(output_path, "PNG")

            # ارسال استیکر
            self.api.send_sticker(user_id, output_path)
            logger.info(f"✅ استیکر ساخته شد برای کاربر {user_id}")

        except Exception as e:
            logger.error(f"❌ خطا در ساخت استیکر: {e}")
            self.api.send_message(user_id, "⚠️ مشکلی در ساخت استیکر پیش آمد.")
