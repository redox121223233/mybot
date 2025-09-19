import os
import logging
from PIL import Image, ImageDraw, ImageFont

class StickerManager:
    def __init__(self, api, db_manager, storage_dir="stickers"):
        self.api = api
        self.db_manager = db_manager
        self.storage_dir = storage_dir

        # پوشه استیکرها رو بسازیم اگه وجود نداره
        os.makedirs(self.storage_dir, exist_ok=True)

    def create_sticker(self, user_id, text, image_path=None, font="arial.ttf", font_size=48, color="white", position="center"):
        """
        ساخت استیکر با متن و (اختیاری) عکس
        """
        try:
            if image_path and os.path.exists(image_path):
                img = Image.open(image_path).convert("RGBA")
            else:
                img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))  # پس‌زمینه شفاف

            draw = ImageDraw.Draw(img)
            font = ImageFont.truetype(font, font_size)

            text_w, text_h = draw.textsize(text, font=font)

            if position == "center":
                pos = ((img.width - text_w) // 2, (img.height - text_h) // 2)
            elif position == "top":
                pos = ((img.width - text_w) // 2, 20)
            elif position == "bottom":
                pos = ((img.width - text_w) // 2, img.height - text_h - 20)
            else:
                pos = (20, 20)

            draw.text(pos, text, font=font, fill=color)

            sticker_path = os.path.join(self.storage_dir, f"{user_id}_{len(os.listdir(self.storage_dir))}.png")
            img.save(sticker_path, "PNG")

            # ذخیره در دیتابیس
            self.db_manager.save("user_packs.json", user_id, {"sticker": sticker_path})

            logging.info(f"Sticker created for user {user_id}: {sticker_path}")
            return sticker_path

        except Exception as e:
            logging.error(f"Error creating sticker: {e}")
            return None

    def get_user_stickers(self, user_id):
        """
        دریافت استیکرهای ذخیره‌شده کاربر
        """
        data = self.db_manager.load("user_packs.json")
        return [s["sticker"] for s in data.get(str(user_id), [])]

    def delete_sticker(self, user_id, sticker_path):
        """
        حذف یک استیکر از کاربر
        """
        data = self.db_manager.load("user_packs.json")
        if str(user_id) in data:
            data[str(user_id)] = [s for s in data[str(user_id)] if s["sticker"] != sticker_path]
            self.db_manager.save("user_packs.json", user_id, data[str(user_id)])
            if os.path.exists(sticker_path):
                os.remove(sticker_path)
            logging.info(f"Sticker deleted: {sticker_path}")
