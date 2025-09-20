# services/sticker_manager.py
import os
import time
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

BACK_BTN = {"keyboard": [[{"text": "⬅️ بازگشت"}]], "resize_keyboard": True}

class StickerManager:
    def __init__(self, api, base_dir="stickers"):
        self.api = api
        self.base_dir = base_dir or "stickers"
        os.makedirs(self.base_dir, exist_ok=True)
        self.user_sessions = {}  # {user_id: {"step":..., "pack_name":..., "photo":...}}

    def start_sticker_flow(self, user_id):
        self.user_sessions[user_id] = {"step": "pack_name"}
        logger.info(f"Sticker flow started for {user_id}")

    def is_in_sticker_flow(self, user_id):
        return user_id in self.user_sessions

    def cancel_flow(self, user_id):
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        self.api.send_message(user_id, "🔙 به منوی اصلی برگشتی.", reply_markup=self._main_menu_kb())

    def set_pack_name(self, user_id, pack_name):
        session = self.user_sessions.get(user_id)
        if not session:
            self.start_sticker_flow(user_id)
            session = self.user_sessions[user_id]
        session["pack_name"] = pack_name.strip() or "default"
        session["step"] = "photo"
        self.api.send_message(user_id, "📸 عکس را ارسال کن.", reply_markup=BACK_BTN)

    def process_sticker_photo(self, user_id, file_id):
        session = self.user_sessions.get(user_id)
        if not session or session.get("step") != "photo":
            self.api.send_message(user_id, "❌ لطفاً از منوی اصلی شروع کنید.", reply_markup=self._main_menu_kb())
            return

        try:
            fname = f"{user_id}_{int(time.time())}.jpg"
            dest = os.path.join(self.base_dir, fname)
            local_path = self.api.download_file(file_id, dest)
            session["photo"] = local_path
            session["step"] = "text"
            self.api.send_message(user_id, "✍️ متن استیکر را بفرست.", reply_markup=BACK_BTN)
        except Exception as e:
            logger.exception("❌ خطا در دانلود عکس")
            self.api.send_message(user_id, "❌ خطا در دانلود عکس. دوباره تلاش کن.", reply_markup=BACK_BTN)

    def add_text_to_sticker(self, user_id, text, style="default"):
        session = self.user_sessions.get(user_id)
        if not session or "photo" not in session:
            self.api.send_message(user_id, "❌ ابتدا استیکرساز را از منوی اصلی شروع کن.", reply_markup=self._main_menu_kb())
            return

        photo_path = session["photo"]
        pack_name = session.get("pack_name", "default")
        out_dir = os.path.join(self.base_dir, "packs", pack_name)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{user_id}_{int(time.time())}.png")

        try:
            img = Image.open(photo_path).convert("RGBA")
            draw = ImageDraw.Draw(img)

            try:
                font = ImageFont.truetype("arial.ttf", 48)
            except:
                font = ImageFont.load_default()

            W, H = img.size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            pos = ((W - text_w) // 2, H - text_h - 30)

            # 🎨 استایل‌ها
            if style == "shadow":
                draw.text((pos[0]+2, pos[1]+2), text, font=font, fill="black")  # سایه
                draw.text(pos, text, font=font, fill="white")

            elif style == "outline":
                for dx in (-2, 2):
                    for dy in (-2, 2):
                        draw.text((pos[0]+dx, pos[1]+dy), text, font=font, fill="black")
                draw.text(pos, text, font=font, fill="yellow")

            elif style == "box":
                # پس‌زمینه رنگی پشت متن
                padding = 10
                box_pos = (pos[0]-padding, pos[1]-padding, pos[0]+text_w+padding, pos[1]+text_h+padding)
                draw.rectangle(box_pos, fill=(0, 0, 0, 180))
                draw.text(pos, text, font=font, fill="white")

            else:  # پیش‌فرض
                draw.text(pos, text, font=font, fill="yellow")

            img.save(out_path, "PNG")
            self.api.send_photo(user_id, out_path, caption=f"✅ استیکر ساخته شد — پک: {pack_name}")

            if user_id in self.user_sessions:
                del self.user_sessions[user_id]

            self.api.send_message(user_id, "⬅️ به منوی اصلی برگشتی.", reply_markup=self._main_menu_kb())

        except Exception as e:
            logger.exception("❌ خطا در ساخت استیکر")
            self.api.send_message(user_id, "❌ مشکلی در ساخت استیکر پیش آمد. دوباره تلاش کن.", reply_markup=self._main_menu_kb())

    def _main_menu_kb(self):
        return {
            "keyboard": [
                [{"text": "🎭 استیکرساز"}, {"text": "🤖 هوش مصنوعی"}],
                [{"text": "⭐ اشتراک"}, {"text": "🎁 تست رایگان"}],
                [{"text": "ℹ️ درباره ما"}],
            ],
            "resize_keyboard": True,
        }

