# services/sticker_manager.py
import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class StickerManager:
    def __init__(self, api, base_dir):
        self.api = api
        self.base_dir = base_dir or "data/stickers"
        os.makedirs(self.base_dir, exist_ok=True)
        self.user_flows = {}  # user_id -> flow dict

    # فلو: pack_name -> photo -> text -> done
    def start_flow(self, user_id):
        self.user_flows[user_id] = {"step": "pack_name"}
        logger.info(f"Sticker flow started for {user_id}")

    def cancel_flow(self, user_id):
        if user_id in self.user_flows:
            del self.user_flows[user_id]
            logger.info(f"Sticker flow canceled for {user_id}")

    def is_in_flow(self, user_id):
        return user_id in self.user_flows

    def get_flow(self, user_id):
        return self.user_flows.get(user_id)

    def set_pack_name(self, user_id, pack_name):
        flow = self.user_flows.get(user_id)
        if not flow: return
        flow["pack_name"] = pack_name.strip()
        flow["step"] = "photo"
        logger.info(f"Pack name set for {user_id}: {pack_name}")

    def process_sticker_photo(self, user_id, file_id):
        flow = self.user_flows.get(user_id)
        if not flow or flow.get("step") != "photo":
            return
        photo_path = os.path.join(self.base_dir, f"{user_id}_src.png")
        try:
            self.api.download_file(file_id, photo_path)
            flow["photo_path"] = photo_path
            flow["step"] = "text"
            self.api.send_message(user_id, "✍️ حالا متن استیکر را ارسال کن (یا /skip برای بدون متن).", reply_markup={"keyboard":[["⬅️ بازگشت"]], "resize_keyboard":True})
        except Exception as e:
            logger.error(f"❌ خطا در دانلود عکس: {e}")
            self.api.send_message(user_id, "❌ خطا در دریافت عکس. دوباره امتحان کن.", reply_markup={"keyboard":[["⬅️ بازگشت"]], "resize_keyboard":True})

    def add_text_to_sticker(self, user_id, text):
        flow = self.user_flows.get(user_id)
        if not flow or flow.get("step") != "text":
            return
        src = flow.get("photo_path")
        pack_name = flow.get("pack_name") or f"pack_{user_id}"
        if not src:
            self.api.send_message(user_id, "❌ عکس موجود نیست. از ابتدا امتحان کن.")
            self.cancel_flow(user_id)
            return

        try:
            final = self._make_sticker_png(src, text, user_id)
            # send sticker to user
            try:
                self.api.send_sticker(user_id, final)
            except Exception as e:
                logger.warning(f"send_sticker failed: {e}")

            # try create or add to set
            bot_username = self.api.username or "bot"
            safe_name = self._safe_pack_name(pack_name, bot_username)
            title = f"{pack_name}"

            if not self.api.sticker_set_exists(safe_name):
                r = self.api.create_new_sticker_set(user_id, safe_name, title, final, emoji="😀")
                if not r.get("ok"):
                    logger.error(f"❌ خطا در ساخت پک: {r}")
                    self.api.send_message(user_id, "❌ خطا در ساخت پک.")
                else:
                    self.api.send_message(user_id, f"✅ پک ساخته شد:\nhttps://t.me/addstickers/{safe_name}")
            else:
                r = self.api.add_sticker_to_set(user_id, safe_name, final, emoji="😀")
                if not r.get("ok"):
                    logger.error(f"❌ خطا در اضافه کردن استیکر: {r}")
                    self.api.send_message(user_id, "❌ خطا در اضافه کردن استیکر.")
                else:
                    self.api.send_message(user_id, f"✅ استیکر اضافه شد:\nhttps://t.me/addstickers/{safe_name}")

            # پاک کردن فلو
            del self.user_flows[user_id]
        except Exception as e:
            logger.exception("❌ خطا در ساخت استیکر")
            self.api.send_message(user_id, "❌ مشکلی در ساخت استیکر پیش آمد.")

    # helper: create 512x512 png with optional text overlay
    def _make_sticker_png(self, src_path, text, user_id):
        # open and convert
        im = Image.open(src_path).convert("RGBA")
        # resize/pad to 512x512 keeping aspect ratio
        target = 512
        ratio = min(target / im.width, target / im.height)
        new_w = int(im.width * ratio)
        new_h = int(im.height * ratio)
        im = im.resize((new_w, new_h), Image.LANCZOS)

        # create transparent background
        final = Image.new("RGBA", (target, target), (0,0,0,0))
        paste_x = (target - new_w) // 2
        paste_y = (target - new_h) // 2
        final.paste(im, (paste_x, paste_y), im if im.mode == "RGBA" else None)

        # add text if exists
        if text and text.strip() and text.strip() != "/skip":
            draw = ImageDraw.Draw(final)
            # font try
            font_path = None
            # look for any font in data/fonts
            fonts_dir = os.path.join(os.path.dirname(__file__), "..", "data", "fonts")
            fonts_dir = os.path.abspath(fonts_dir)
            font = None
            try:
                # try Arial or any default TTF
                font_candidates = [
                    os.path.join(fonts_dir, "arial.ttf"),
                    os.path.join(fonts_dir, "Roboto-Bold.ttf"),
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                ]
                for p in font_candidates:
                    if p and os.path.exists(p):
                        font = ImageFont.truetype(p, 48)
                        break
            except Exception:
                font = None
            if font is None:
                font = ImageFont.load_default()

            # measure
            try:
                bbox = draw.textbbox((0,0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
            except Exception:
                text_w, text_h = font.getsize(text)

            # position bottom center by default
            x = (target - text_w) // 2
            y = target - text_h - 20

            # draw outline for readability
            outline_color = (0,0,0,200)
            for ox, oy in [(-2,-2),(2,-2),(-2,2),(2,2),(0,0)]:
                draw.text((x+ox, y+oy), text, font=font, fill=outline_color)
            # main white text
            draw.text((x, y), text, font=font, fill=(255,255,255,255))

        # save final
        out_path = os.path.join(self.base_dir, f"{user_id}_final.png")
        final.save(out_path, format="PNG")
        return out_path

    def _safe_pack_name(self, pack_name, bot_username):
        # make Telegram-compliant short name: letters/numbers/_ only, must end with _by_botusername
        base = "".join(c if c.isalnum() else "_" for c in pack_name.lower()).strip("_")
        if not base:
            base = f"pack_{abs(hash(pack_name))%10000}"
        botname = (bot_username or "bot").replace("@", "")
        name = f"{base}_by_{botname}"
        # max length validation (Telegram allows up to 64)
        return name[:64]
