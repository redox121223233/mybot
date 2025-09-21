import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, api, base_dir="data/stickers", fonts_dir="data/fonts"):
        self.api = api
        self.base_dir = base_dir
        self.fonts_dir = fonts_dir
        self.user_flows = {}

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)

    def start_flow(self, user_id):
        self.user_flows[user_id] = {"step": "pack_name"}
        self.api.send_message(user_id, "📦 نام پکیج استیکر را وارد کنید:")

    def cancel_flow(self, user_id):
        if user_id in self.user_flows:
            del self.user_flows[user_id]

    def set_pack_name(self, user_id, pack_name):
        self.user_flows[user_id]["pack_name"] = pack_name
        self.user_flows[user_id]["step"] = "photo"
        self.api.send_message(user_id, "📷 لطفاً عکس استیکر را ارسال کنید:")

    def process_photo(self, user_id, file_id):
        flow = self.user_flows.get(user_id)
        if not flow or flow["step"] != "photo":
            return

        path = os.path.join(self.base_dir, f"{user_id}_sticker.png")
        self.api.download_file(file_id, path)
        flow["photo_path"] = path
        flow["step"] = "text"

        self.api.send_message(user_id, "✍️ متن مورد نظر برای استیکر را ارسال کنید:")

    def add_text_and_build(self, user_id, text):
        flow = self.user_flows.get(user_id)
        if not flow or flow["step"] != "text":
            return

        photo_path = flow["photo_path"]
        pack_name = flow["pack_name"]

        final_path = os.path.join(self.base_dir, f"{user_id}_final.png")

        # ------------------ فونت ------------------
        font_path = self._default_font()
        try:
            font = ImageFont.truetype(font_path, 60)
        except:
            font = ImageFont.load_default()

        image = Image.open(photo_path).convert("RGBA")
        draw = ImageDraw.Draw(image)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (image.width - text_w) // 2, image.height - text_h - 20
        draw.text((x, y), text, font=font, fill="white")

        # تغییر اندازه به 512x512
        image = image.resize((512, 512))
        image.save(final_path, "PNG")

        # ------------------ استیکر پک ------------------
        set_name = f"pack_{user_id}_by_{self.api.username}"
        title = f"پک {user_id}"

        if not self.api.sticker_set_exists(set_name):
            self.api.create_new_sticker_set(user_id, set_name, title, final_path)
        else:
            self.api.add_sticker_to_set(user_id, set_name, final_path)

        # ارسال استیکر + لینک پک
        self.api.send_sticker(user_id, final_path)
        self.api.send_message(user_id, f"✅ استیکر ساخته شد!\n🔗 لینک پک:\nhttps://t.me/addstickers/{set_name}")

        del self.user_flows[user_id]

    def _default_font(self):
        try:
            fonts = [f for f in os.listdir(self.fonts_dir) if f.endswith(".ttf")]
            if fonts:
                return os.path.join(self.fonts_dir, fonts[0])
        except:
            pass
        return None
