import os
import logging
from PIL import Image, ImageDraw, ImageFont
from utils.telegram_api import TelegramAPI

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, api: TelegramAPI, base_dir="stickers"):
        self.api = api
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

        # وضعیت کاربرها (جریان ساخت استیکر)
        self.user_flows = {}  
        # ساختار: {user_id: {"step": "pack_name/photo/text", "pack_name": "", "photo_path": ""}}

    def start_sticker_flow(self, user_id):
        """شروع جریان ساخت استیکر"""
        self.user_flows[user_id] = {"step": "pack_name"}
        logger.info(f"Sticker flow started for user {user_id}")

    def is_in_sticker_flow(self, user_id):
        """بررسی اینکه کاربر توی جریان استیکرساز هست یا نه"""
        return user_id in self.user_flows

    def process_sticker_step(self, user_id, text=None, file_id=None):
        """پردازش مراحل ساخت استیکر"""
        flow = self.user_flows.get(user_id)
        if not flow:
            return

        step = flow["step"]

        # مرحله ۱ → گرفتن نام پک
        if step == "pack_name" and text:
            flow["pack_name"] = text
            flow["step"] = "photo"
            self.api.send_message(user_id, "📸 حالا یک عکس ارسال کنید تا استیکر ساخته بشه.")
            return

        # مرحله ۲ → گرفتن عکس
        if step == "photo" and file_id:
            file_path = os.path.join(self.base_dir, f"{user_id}_photo.jpg")
            try:
                self.api.download_file(file_id, file_path)
                flow["photo_path"] = file_path
                flow["step"] = "text"
                self.api.send_message(user_id, "✍️ عالی! حالا متنی که روی استیکر باشه رو بفرست.")
            except Exception as e:
                logger.error(f"خطا در دانلود عکس: {e}")
                self.api.send_message(user_id, "❌ خطا در دریافت عکس. دوباره امتحان کنید.")
            return

        # مرحله ۳ → گرفتن متن و ساخت استیکر
        if step == "text" and text:
            try:
                output_path = os.path.join(self.base_dir, f"{user_id}_sticker.png")
                self._create_sticker(flow["photo_path"], text, output_path)

                with open(output_path, "rb") as f:
                    self.api.send_photo(user_id, f, caption=f"✅ استیکر ساخته شد! پک: {flow['pack_name']}")

                # پاک کردن جریان بعد از اتمام
                del self.user_flows[user_id]
            except Exception as e:
                logger.error(f"خطا در ساخت استیکر: {e}")
                self.api.send_message(user_id, "❌ مشکلی در ساخت استیکر پیش اومد.")
            return

    def _create_sticker(self, photo_path, text, output_path):
        """ساخت استیکر با متن روی عکس"""
        img = Image.open(photo_path).convert("RGBA")
        draw = ImageDraw.Draw(img)

        # فونت (اگر پیدا نشد از پیش‌فرض استفاده میشه)
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()

        # موقعیت متن
        W, H = img.size
        w, h = draw.textsize(text, font=font)
        position = ((W - w) // 2, H - h - 20)  # پایین وسط

        # نوشتن متن
        draw.text(position, text, font=font, fill="yellow")

        img.save(output_path, "PNG")
        logger.info(f"Sticker created: {output_path}")
