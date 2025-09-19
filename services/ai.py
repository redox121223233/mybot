from pathlib import Path
from PIL import Image, ImageFont, ImageDraw
from utils.keyboards import send_message

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "assets" / "fonts"
TEMPLATES_DIR = BASE_DIR / "assets" / "templates"

def toggle(chat_id, status):
    send_message(chat_id, f"AI mode set to {status}")

def apply_template(template_name, text):
    template_path = TEMPLATES_DIR / f"{template_name}.png"
    font_path = FONTS_DIR / "Vazir.ttf"

    if not template_path.exists():
        raise FileNotFoundError(template_path)
    if not font_path.exists():
        raise FileNotFoundError(font_path)

    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(font_path), 40)

    draw.text((50, 50), text, font=font, fill="white")
    return img
