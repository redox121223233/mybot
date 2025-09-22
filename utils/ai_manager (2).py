import os
import logging
from PIL import Image, ImageDraw, ImageFont
from config import FONTS_DIR
from utils.sticker_manager import get_user_settings

logger = logging.getLogger(__name__)

def generate_sticker(user_id: int, text: str, image_path: str = None) -> str:
    try:
        settings = get_user_settings(user_id)
        font_path = os.path.join(FONTS_DIR, settings["font"])
        font_size = settings.get("font_size", 48)
        color = settings.get("font_color", "black")
        position = settings.get("position", "center")

        if image_path and os.path.exists(image_path):
            img = Image.open(image_path).convert("RGBA")
        else:
            img = Image.new("RGBA", (512, 512), "white")

        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_path, font_size)

        text_w, text_h = draw.textsize(text, font=font)
        if position == "top":
            xy = ((img.width - text_w) // 2, 20)
        elif position == "bottom":
            xy = ((img.width - text_w) // 2, img.height - text_h - 20)
        else:
            xy = ((img.width - text_w) // 2, (img.height - text_h) // 2)

        draw.text(xy, text, font=font, fill=color)

        out_path = f"/tmp/sticker_{user_id}.png"
        img.save(out_path, "PNG")
        return out_path
    except Exception as e:
        logger.error(f"❌ Error in generate_sticker: {e}")
        return None
