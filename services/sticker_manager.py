import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, api, base_dir="stickers"):
        self.api = api
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def build_sticker(self, user_id, flow):
        try:
            file_path = os.path.join(self.base_dir, f"{user_id}_photo.png")
            self.api.download_file(flow["photo_id"], file_path)

            image = Image.open(file_path).convert("RGBA")
            draw = ImageDraw.Draw(image)

            # انتخاب فونت
            font_name = "arial.ttf"
            if flow["font"] == "بولد":
                font_name = "arialbd.ttf"
            elif flow["font"] == "نستعلیق":
                font_name = "nazanin.ttf"  # باید این فونت رو تو پروژه بذاری
            try:
                font = ImageFont.truetype(font_name, 60)
            except:
                font = ImageFont.load_default()

            # انتخاب رنگ
            colors = {"⚪️ سفید": "white", "🔴 قرمز": "red", "🔵 آبی": "blue", "🟢 سبز": "green"}
            color = colors.get(flow["color"], "white")

            # موقعیت متن
            bbox = draw.textbbox((0, 0), flow["sticker_text"], font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if flow["position"] == "⬆️ بالا":
                x, y = (image.width - text_w) // 2, 20
            elif flow["position"] == "⬇️ پایین":
                x, y = (image.width - text_w) // 2, image.height - text_h - 20
            else:  # وسط
                x, y = (image.width - text_w) // 2, (image.height - text_h) // 2

            draw.text((x, y), flow["sticker_text"], font=font, fill=color)

            final_path = os.path.join(self.base_dir, f"{user_id}_final.png")
            image.save(final_path)

            # ارسال استیکر (عکس به عنوان استیکر تستی)
            self.api.send_sticker(user_id, final_path)

            # لینک پک
            pack_name = f"pack_{user_id}_by_{self.api.username}"
            self.api.send_message(
                user_id,
                f"✅ استیکر ساخته شد!\n\n🔗 لینک پک شما:\nhttps://t.me/addstickers/{pack_name}"
            )

        except Exception as e:
            logger.error(f"❌ خطا در ساخت استیکر: {e}")
            self.api.send_message(user_id, "❌ مشکلی در ساخت استیکر پیش آمد.")
