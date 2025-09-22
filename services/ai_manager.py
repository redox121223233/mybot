import os
from PIL import Image, ImageDraw, ImageFont
from config import DATA_DIR, FONTS_DIR

DEFAULT_FONT = os.path.join(FONTS_DIR, "Vazirmatn-Regular.ttf")

def generate_sticker(text: str, user_id: int, font_size=48, color="white"):
    """ساخت استیکر ساده با متن روی پس‌زمینه شفاف"""
    width, height = 512, 512
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype(DEFAULT_FONT, font_size)
    except:
        font = ImageFont.load_default()

    w, h = draw.textsize(text, font=font)
    draw.text(((width - w) / 2, (height - h) / 2),
              text, font=font, fill=color)

    path = os.path.join(DATA_DIR, f"ai_sticker_{user_id}.png")
    img.save(path, "PNG")
    return path
