import os
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self, api, base_dir="data/ai", fonts_dir="data/fonts"):
        self.api = api
        self.base_dir = base_dir
        self.fonts_dir = fonts_dir
        self.user_settings = {}  # user_id -> {"color":..., "position":..., "font":...}

        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)

    # ------------------ مدیریت تنظیمات ------------------
    def reset_settings(self, user_id):
        self.user_settings[user_id] = {
            "color": (255, 255, 255, 255),  # سفید
            "position": "bottom-center",
            "font": self._default_font()
        }
        logger.info(f"🔄 تنظیمات ریست شد برای {user_id}")

    def set_color(self, user_id, color_name):
        colors = {
            "سفید": (255, 255, 255, 255),
            "مشکی": (0, 0, 0, 255),
            "زرد": (255, 215, 0, 255),
            "قرمز": (255, 0, 0, 255)
        }
        self.user_settings[user_id]["color"] = colors.get(color_name, (255, 255, 255, 255))
        logger.info(f"🎨 رنگ برای {user_id} تغییر کرد: {color_name}")

    def set_position(self, user_id, pos):
        self.user_settings[user_id]["position"] = pos
        logger.info(f"📍 موقعیت متن برای {user_id} تغییر کرد: {pos}")

    def set_font(self, user_id, font_name):
        path = os.path.join(self.fonts_dir, font_name)
        if os.path.exists(path):
            self.user_settings[user_id]["font"] = path
            logger.info(f"🔤 فونت برای {user_id} تغییر کرد: {font_name}")

    def _default_font(self):
        try:
            fonts = [f for f in os.listdir(self.fonts_dir) if f.endswith(".ttf")]
            if fonts:
                return os.path.join(self.fonts_dir, fonts[0])
        except Exception:
            pass
        return None

    def get_settings(self, user_id):
        if user_id not in self.user_settings:
            self.reset_settings(user_id)
        return self.user_settings[user_id]

    # ------------------ پردازش عکس ------------------
    def add_text_to_image(self, user_id, image_path, text, output_path):
        settings = self.get_settings(user_id)

        image = Image.open(image_path).convert("RGBA")
        draw = ImageDraw.Draw(image)

        # انتخاب فونت
        font_path = settings.get("font")
        try:
            if font_path and os.path.exists(font_path):
                font = ImageFont.truetype(font_path, 48)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        # متن
        color = settings.get("color", (255, 255, 255, 255))
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # موقعیت
        pos_name = settings.get("position", "bottom-center")
        if pos_name == "bottom-center":
            pos = ((image.width - text_w) // 2, image.height - text_h - 20)
        elif pos_name == "top-center":
            pos = ((image.width - text_w) // 2, 20)
        elif pos_name == "center":
            pos = ((image.width - text_w) // 2, (image.height - text_h) // 2)
        elif pos_name == "bottom-left":
            pos = (20, image.height - text_h - 20)
        elif pos_name == "bottom-right":
            pos = (image.width - text_w - 20, image.height - text_h - 20)
        else:
            pos = (20, 20)

        # نوشتن متن
        draw.text(pos, text, font=font, fill=color)

        # ذخیره
        image.save(output_path, "PNG")
        logger.info(f"✅ عکس نهایی ساخته شد: {output_path}")
        return output_path
