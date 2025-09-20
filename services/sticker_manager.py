import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont

class StickerManager:
    def __init__(self, api, base_dir):
        self.api = api
        self.base_dir = base_dir
        self.user_sessions = {}

    # مرحله ۱: گرفتن اسم پک
    def start_sticker_flow(self, user_id):
        self.user_sessions[user_id] = {"step": "pack_name"}
        self.api.send_message(
            user_id,
            "✍️ لطفاً نام پک استیکر خود را وارد کنید:",
            reply_markup=self.api.get_back_button()
        )

    def set_pack_name(self, user_id, pack_name):
        self.user_sessions[user_id] = {"step": "photo", "pack_name": pack_name}
        self.api.send_message(
            user_id,
            "📸 حالا یک عکس بفرست.",
            reply_markup=self.api.get_back_button()
        )

    # مرحله ۲: گرفتن عکس
    def process_sticker_photo(self, user_id, file_id):
        session = self.user_sessions.get(user_id, {})
        if not session or session.get("step") != "photo":
            self.api.send_message(user_id, "❌ لطفاً اول اسم پک رو بده.", reply_markup=self.api.main_menu())
            return

        photo_path = f"/tmp/{user_id}_{int(time.time())}.jpg"
        self.api.download_file(file_id, photo_path)

        session["photo"] = photo_path
        session["step"] = "text"

        self.api.send_message(
            user_id,
            "✍️ متن دلخواه برای استیکر رو بفرست.",
            reply_markup=self.api.get_back_button()
        )

    # مرحله ۳: گرفتن متن و ساخت استیکر
    def add_text_to_sticker(self, user_id, text):
        session = self.user_sessions.get(user_id, {})
        if not session or session.get("step") != "text":
            self.api.send_message(user_id, "❌ لطفاً اول عکس بده.", reply_markup=self.api.main_menu())
            return

        pack_name = session["pack_name"]
        photo_path = session["photo"]

        # ساخت متن روی عکس
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

        draw.text(pos, text, font=font, fill="white")

        # ذخیره در فرمت WEBP
        webp_path = f"/tmp/{user_id}_{int(time.time())}.webp"
        img.save(webp_path, "WEBP")

        # مرحله ۴: اضافه به پک
        self.ensure_pack_exists(user_id, pack_name, webp_path)
        self.add_sticker_to_pack(user_id, pack_name, webp_path)

        # پایان جریان
        self.user_sessions[user_id] = {}
        self.api.send_message(user_id, "✅ استیکر ساخته شد و به پک اضافه شد!", reply_markup=self.api.main_menu())

    # بررسی وجود پک یا ایجاد آن
    def ensure_pack_exists(self, user_id, pack_name, sticker_path):
        url = f"https://api.telegram.org/bot{self.api.token}/createNewStickerSet"
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": user_id,
                "name": f"{pack_name}_by_{self.api.username}",
                "title": f"{pack_name} Pack",
                "emojis": "😎"
            }
            r = requests.post(url, data=data, files=files)

        if not r.json().get("ok") and "already" not in r.text.lower():
            self.api.send_message(user_id, f"❌ خطا در ساخت پک: {r.text}")

    # اضافه کردن استیکر به پک
    def add_sticker_to_pack(self, user_id, pack_name, sticker_path):
        url = f"https://api.telegram.org/bot{self.api.token}/addStickerToSet"
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": user_id,
                "name": f"{pack_name}_by_{self.api.username}",
                "emojis": "🔥"
            }
            r = requests.post(url, data=data, files=files)

        if not r.json().get("ok"):
            self.api.send_message(user_id, f"❌ خطا در اضافه کردن استیکر: {r.text}")

    # وضعیت کاربر
    def is_in_sticker_flow(self, user_id):
        return self.user_sessions.get(user_id, {}).get("step") in ["pack_name", "photo", "text"]
