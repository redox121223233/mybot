import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, api, base_dir="stickers"):
        self.api = api
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

        # مدیریت جریان استیکر سازی
        self.user_flows = {}

    # شروع فلو استیکر سازی
    def start_sticker_flow(self, user_id):
        self.user_flows[user_id] = {"step": "pack_name"}
        logger.info(f"🎭 Sticker flow started for {user_id}")

    # لغو فلو
    def cancel_flow(self, user_id):
        if user_id in self.user_flows:
            del self.user_flows[user_id]
            logger.info(f"↩️ Sticker flow canceled for {user_id}")

    # چک کردن اینکه کاربر داخل فلو هست یا نه
    def is_in_sticker_flow(self, user_id):
        return user_id in self.user_flows

    # مرحله ۱: گرفتن اسم پک
    def set_pack_name(self, user_id, pack_name):
        flow = self.user_flows.get(user_id)
        if not flow:
            return

        flow["pack_name"] = pack_name
        flow["step"] = "photo"
        logger.info(f"📦 Pack name set for {user_id}: {pack_name}")
        self.api.send_message(
            user_id,
            "📷 لطفاً عکس خود را ارسال کنید:",
            reply_markup={"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}
        )

    # مرحله ۲: پردازش عکس
    def process_sticker_photo(self, user_id, file_id):
        flow = self.user_flows.get(user_id)
        if not flow or flow.get("step") != "photo":
            return

        file_path = os.path.join(self.base_dir, f"{user_id}_sticker.png")

        try:
            self.api.download_file(file_id, file_path)
            flow["photo_path"] = file_path
            flow["step"] = "text"
            logger.info(f"📷 Photo saved for {user_id}: {file_path}")

            self.api.send_message(
                user_id,
                "✍️ متن مورد نظر خود را برای استیکر وارد کنید:",
                reply_markup={"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}
            )
        except Exception as e:
            logger.error(f"❌ خطا در دانلود عکس: {e}")
            self.api.send_message(user_id, "❌ خطا در دریافت عکس. دوباره امتحان کنید.")

    # مرحله ۳: اضافه کردن متن به عکس و ساخت استیکر
    def add_text_to_sticker(self, user_id, text):
        flow = self.user_flows.get(user_id)
        if not flow or flow.get("step") != "text":
            return

        photo_path = flow.get("photo_path")
        pack_name = flow.get("pack_name")

        if not photo_path or not pack_name:
            self.api.send_message(user_id, "❌ مشکلی در جریان استیکر سازی پیش آمد.")
            return

        try:
            # باز کردن تصویر
            image = Image.open(photo_path).convert("RGBA")
            draw = ImageDraw.Draw(image)

            # انتخاب فونت
            try:
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                font = ImageFont.load_default()

            # موقعیت متن
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x, y = (image.width - text_w) // 2, image.height - text_h - 20

            # نوشتن متن
            draw.text((x, y), text, font=font, fill="white")

            # تغییر سایز به ابعاد مجاز تلگرام
            max_size = 512
            image.thumbnail((max_size, max_size), Image.LANCZOS)

            # ذخیره نسخه نهایی
            final_path = os.path.join(self.base_dir, f"{user_id}_final.png")
            image.save(final_path, format="PNG")

            # ساخت یا اضافه کردن به پک
            sticker_set_name = f"pack_{user_id}_by_{self.api.username}"
            title = f"استیکرهای {user_id}"

            if not self.api.sticker_set_exists(sticker_set_name):
                created = self.api.create_new_sticker_set(
                    user_id,
                    sticker_set_name,
                    title,
                    final_path,
                    emoji="😀"
                )
                if not created:
                    self.api.send_message(user_id, "❌ خطا در ساخت پک.")
                    return
            else:
                added = self.api.add_sticker_to_set(
                    user_id,
                    sticker_set_name,
                    final_path,
                    emoji="😀"
                )
                if not added:
                    self.api.send_message(user_id, "❌ خطا در اضافه کردن استیکر.")
                    return

            # پاک کردن جریان کاربر
            del self.user_flows[user_id]

            # ارسال استیکر ساخته شده
            self.api.send_sticker(user_id, final_path)

            # ارسال لینک پک
            self.api.send_message(
                user_id,
                f"✅ استیکر ساخته شد!\n\n🔗 لینک پک شما:\nhttps://t.me/addstickers/{sticker_set_name}"
            )

        except Exception as e:
            logger.error(f"❌ خطا در ساخت استیکر: {e}")
            self.api.send_message(user_id, "❌ مشکلی در ساخت استیکر پیش آمد.")
