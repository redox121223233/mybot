# mybot/services/ai_manager.py
import os
from PIL import Image, ImageDraw, ImageFont
from utils.logger import logger


class AIManager:
    """
    شبیه‌ساز هوش مصنوعی برای طراحی متن روی عکس.
    کاربر می‌تواند متن و تنظیمات را بدهد:
    - text: متن
    - position: موقعیت ("top", "center", "bottom")
    - color: رنگ (مثل "yellow" یا "#FF0000")
    - font_size: سایز فونت
    - bold: True/False
    """

    def __init__(self, fonts_dir="/usr/share/fonts"):
        self.fonts_dir = fonts_dir
        self.default_font = self._find_default_font()

    def _find_default_font(self):
        # سعی می‌کنیم یک فونت پیدا کنیم (در Docker هم کار کنه)
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        logger.warning("هیچ فونت استاندارد پیدا نشد. از پیش‌فرض PIL استفاده می‌شود.")
        return None

    def apply_text(self, image_path, output_path, text, options=None):
        try:
            options = options or {}
            position = options.get("position", "center")
            color = options.get("color", "yellow")
            font_size = int(options.get("font_size", 48))
            bold = bool(options.get("bold", False))

            # باز کردن عکس
            img = Image.open(image_path).convert("RGBA")
            draw = ImageDraw.Draw(img)

            # انتخاب فونت
            font_path = self.default_font
            if bold and "Bold" not in font_path:
                font_path = font_path.replace(".ttf", "-Bold.ttf") if font_path else None
            try:
                font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
            except:
                font = ImageFont.load_default()

            # محاسبه موقعیت متن
            text_w, text_h = draw.textsize(text, font=font)
            if position == "top":
                xy = ((img.width - text_w) // 2, 10)
            elif position == "bottom":
                xy = ((img.width - text_w) // 2, img.height - text_h - 10)
            else:  # center
                xy = ((img.width - text_w) // 2, (img.height - text_h) // 2)

            # رسم متن
            draw.text(xy, text, font=font, fill=color)

            # ذخیره خروجی
            img.save(output_path, format="PNG")
            logger.info("AIManager: متن روی عکس اعمال شد → %s", output_path)
            return output_path

        except Exception as e:
            logger.exception("AIManager.apply_text failed: %s", e)
            return None
