from pathlib import Path
from PIL import Image, ImageFont, ImageDraw
from utils.telegram_api import send_message
BASE = Path(__file__).resolve().parent.parent
FONTS = BASE / "assets" / "fonts"
TEMPLATES = BASE / "assets" / "templates"

def toggle(chat_id, status):
    send_message(chat_id, f"AI mode set to {status}")

def apply_template(template_name, text):
    tpl = TEMPLATES / f"{template_name}.png"
    font_path = FONTS / "Vazir.ttf"
    if not tpl.exists():
        raise FileNotFoundError(tpl)
    if not font_path.exists():
        raise FileNotFoundError(font_path)
    img = Image.open(tpl).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(font_path), 40)
    draw.text((50,50), text, font=font, fill=(255,255,255,255))
    out = BASE / "data" / f"out_{template_name}.png"
    img.save(out)
    return str(out)
