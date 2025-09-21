# services/ai_manager.py
import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self, api, base_dir):
        self.api = api
        self.base_dir = base_dir or "data/ai"
        os.makedirs(self.base_dir, exist_ok=True)
        self.user_flows = {}  # user_id -> {"step": "idle"|"photo"|"text", "photo_path":...}

    def start_flow(self, user_id):
        self.user_flows[user_id] = {"step": "waiting"}  # waiting for text or photo
        self.api.send_message(user_id, "🤖 هوش مصنوعی فعال شد. می‌تونی متن یا عکس + دستور طراحی ارسال کنی.\nمثال دستور: 'متن: سلام; موقعیت: بالا-راست; رنگ: زرد'")

    def cancel_flow(self, user_id):
        if user_id in self.user_flows:
            del self.user_flows[user_id]

    def is_in_flow(self, user_id):
        return user_id in self.user_flows

    def process_ai_photo(self, user_id, file_id):
        flow = self.user_flows.get(user_id) or {}
        dest = os.path.join(self.base_dir, f"{user_id}_ai.png")
        try:
            self.api.download_file(file_id, dest)
            flow["photo_path"] = dest
            flow["step"] = "awaiting_instructions"
            self.user_flows[user_id] = flow
            self.api.send_message(user_id, "📷 عکس دریافت شد — لطفاً دستور طراحی (متن/موقعیت/رنگ) را ارسال کن.\nمثال: متن: سلام; موقعیت: پایین-وسط; رنگ: سفید")
        except Exception as e:
            logger.error(f"AI: download photo error: {e}")
            self.api.send_message(user_id, "❌ خطا در دریافت عکس.")

    def process_ai_text(self, user_id, text):
        flow = self.user_flows.get(user_id)
        if not flow:
            self.api.send_message(user_id, "ابتدا '🤖 هوش مصنوعی' را از منو انتخاب کن.")
            return

        photo = flow.get("photo_path")
        if not photo:
            # if no photo, we can just echo or do text-only response
            # simple echo-like behaviour
            self.api.send_message(user_id, f"🤖 پاسخ هوش مصنوعی (تکست):\n{text}")
            return

        # parse simple params: متن:, موقعیت:, رنگ:
        parts = {}
        for part in text.split(";"):
            if ":" in part:
                k,v = part.split(":",1)
                parts[k.strip().lower()] = v.strip()

        content = parts.get("متن") or parts.get("text") or text
        color_name = parts.get("رنگ","white")
        position = parts.get("موقعیت","bottom-center")

        # map color
        colors = {"سفید":(255,255,255,255),"white":(255,255,255,255),
                  "مشکی":(0,0,0,255),"black":(0,0,0,255),
                  "زرد":(255,215,0,255),"red":(255,0,0,255)}
        col = colors.get(color_name.lower(), (255,255,255,255))

        try:
            out = self._overlay_text_on_image(photo, content, col, position, user_id)
            # send result image
            self.api.send_message(user_id, "✅ تصویر شما ساخته شد؛ ارسال می‌شود ...")
            try:
                self.api.send_sticker(user_id, out)  # try as sticker first (if 512x512)
            except Exception:
                # fallback: send as photo
                with open(out, "rb") as f:
                    # use sendMessage with photo via Telegram sendPhoto endpoint
                    self.api.request("sendPhoto", params={"chat_id": user_id}, files={"photo": open(out, "rb")})
            self.cancel_flow(user_id)
        except Exception as e:
            logger.exception("AI processing failed")
            self.api.send_message(user_id, "❌ خطا در تولید تصویر.")

    def _overlay_text_on_image(self, path, text, color, position, user_id):
        img = Image.open(path).convert("RGBA")
        # resize similar to sticker (fit into 512 if large)
        target = 512
        if img.width > target or img.height > target:
            ratio = min(target / img.width, target / img.height)
            img = img.resize((int(img.width*ratio), int(img.height*ratio)), Image.LANCZOS)

        final = Image.new("RGBA", (target, target), (0,0,0,0))
        paste_x = (target - img.width)//2
        paste_y = (target - img.height)//2
        final.paste(img, (paste_x, paste_y), img if img.mode == "RGBA" else None)

        draw = ImageDraw.Draw(final)
        # font
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        except Exception:
            font = ImageFont.load_default()

        try:
            bbox = draw.textbbox((0,0), text, font=font)
            tw = bbox[2]-bbox[0]; th = bbox[3]-bbox[1]
        except Exception:
            tw, th = font.getsize(text)

        # position map
        pos = position.replace(" ", "").lower()
        if "top" in pos:
            y = 10
        elif "bottom" in pos:
            y = target - th - 10
        else:
            y = (target - th)//2

        if "left" in pos:
            x = 10
        elif "right" in pos:
            x = target - tw - 10
        else:
            x = (target - tw)//2

        # outline + text
        for ox,oy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
            draw.text((x+ox, y+oy), text, font=font, fill=(0,0,0,200))
        draw.text((x,y), text, font=font, fill=color)

        out = os.path.join(self.base_dir, f"{user_id}_ai_out.png")
        final.save(out, format="PNG")
        return out
