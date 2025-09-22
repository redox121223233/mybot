import logging
from PIL import Image, ImageDraw, ImageFont
import os
from config import FONTS_DIR, DATA_DIR

logger = logging.getLogger(__name__)

def generate_sticker(prompt: str, output_path: str, settings: dict):
    """تولید استیکر بر اساس متن کاربر + تنظیمات ذخیره شده"""
    try:
        img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        font_path = os.path.join(FONTS_DIR, settings.get("font", "Vazir.ttf"))
        font_size = settings.get("font_size", 48)
        font_color = settings.get("font_color", "black")
        position = settings.get("position", "center")

        font = ImageFont.truetype(font_path, font_size)

        text_w, text_h = draw.textsize(prompt, font=font)
        if position == "center":
            pos = ((512 - text_w) // 2, (512 - text_h) // 2)
        elif position == "top":
            pos = ((512 - text_w) // 2, 50)
        elif position == "bottom":
            pos = ((512 - text_w) // 2, 512 - text_h - 50)
        else:
            pos = (50, 50)

        draw.text(pos, prompt, font=font, fill=font_color)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, "PNG")
        logger.info(f"✅ Sticker generated: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"❌ Error generating sticker: {e}")
        raise
