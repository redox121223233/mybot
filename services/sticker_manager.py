# services/sticker_manager.py
import os
import time
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

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
        # inform user done
        self.api.send_message(user_id, "🔙 برگشت به منوی اصلی.", reply_markup={"keyboard":[[{"text":"⬅️ بازگشت"}]], "resize_keyboard": True})

    def set_pack_name(self, user_id, pack_name):
        session = self.user_sessions.get(user_id)
        if not session:
            self.start_sticker_flow(user_id)
            session = self.user_sessions[user_id]
        session["pack_name"] = pack_name.strip() or "default"
        session["step"] = "photo"
        self.api.send_message(user_id, "📸 حالا عکس را ارسال کنید.", reply_markup={"keyboard":[[{"text":"⬅️ بازگشت"}]], "resize_keyboard": True})
        logger.info(f"User {user_id} set pack name: {session['pack_name']}")

    def process_sticker_photo(self, user_id, file_id):
        session = self.user_sessions.get(user_id)
        if not session:
            self.api.send_message(user_id, "ابتدا از منوی اصلی استیکرساز را انتخاب کنید.", reply_markup=self._main_menu_kb())
            return

        if session.get("step") != "photo":
            self.api.send_message(user_id, "در حال حاضر منتظر عکس نیستیم. اگر می‌خواهید از اول شروع کنید، دکمه بازگشت را بزنید.", reply_markup=self._main_menu_kb())
            return

        try:
            # filename unique with timestamp
            fname = f"{user_id}_{int(time.time())}.jpg"
            dest = os.path.join(self.base_dir, fname)
            local_path = self.api.download_file(file_id, dest)
            session["photo"] = local_path
            session["step"] = "text"
            self.api.send_message(user_id, "✍️ عکس دریافت شد. الآن متن استیکر را بفرستید.", reply_markup={"keyboard":[[{"text":"⬅️ بازگشت"}]], "resize_keyboard": True})
            logger.info(f"Downloaded user {user_id} photo to {local_path}")
        except Exception as e:
            logger.exception("خطا در دانلود عکس")
            self.api.send_message(user_id, "❌ خطا در دانلود عکس. لطفاً دوباره تلاش کنید یا عکس دیگری بفرستید.", reply_markup={"keyboard":[[{"text":"⬅️ بازگشت"}]], "resize_keyboard": True})

    def add_text_to_sticker(self, user_id, text):
        session = self.user_sessions.get(user_id)
        if not session or "photo" not in session:
            self.api.send_message(user_id, "عکسی برای ساخت استیکر پیدا نشد. لطفاً از ابتدا شروع کنید.", reply_markup=self._main_menu_kb())
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
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()

            W, H = img.size
            text_w, text_h = draw.textsize(text, font=font)
            pos = ((W - text_w) // 2, H - text_h - 20)
            draw.text(pos, text, font=font, fill="yellow")

            img.save(out_path, "PNG")
            # ارسال فایل به کاربر (به عنوان عکس یا استیکر)
            self.api.send_photo(user_id, out_path, caption=f"✅ استیکر ساخته شد — پک: {pack_name}")
            logger.info(f"Sticker saved: {out_path}")

            # پایان جریان
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]

        except Exception as e:
            logger.exception("خطا در ساخت استیکر")
            self.api.send_message(user_id, "❌ خطا در ساخت استیکر. لطفاً دوباره تلاش کنید.", reply_markup=self._main_menu_kb())

    def _main_menu_kb(self):
        return {"keyboard":[[{"text":"🎭 استیکرساز"},{"text":"🤖 هوش مصنوعی"}],[{"text":"⭐ اشتراک"},{"text":"🎁 تست رایگان"}],[{"text":"ℹ️ درباره ما"}]], "resize_keyboard": True}
