import os
from io import BytesIO
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
LOCAL_FONT_FILES = {
    "Vazirmatn": "Vazirmatn-Regular.ttf",
    "NotoNaskh": "NotoNaskhArabic-Regular.ttf",
    "Sahel": "Sahel.ttf",
    "IRANSans": "IRANSans.ttf",
    "Roboto": "Roboto-Regular.ttf",
    "Default": "Vazirmatn-Regular.ttf"
}
_LOCAL_FONTS = {k: os.path.join(FONT_DIR, v) for k, v in LOCAL_FONT_FILES.items() if os.path.exists(os.path.join(FONT_DIR, v))}

def resolve_font_path(font_key: Optional[str], text: str = "") -> str:
    if font_key and font_key in _LOCAL_FONTS:
        return _LOCAL_FONTS[font_key]
    is_persian = any('\u0600' <= char <= '\u06FF' for char in text)
    return _LOCAL_FONTS.get("Vazirmatn" if is_persian else "Roboto", next(iter(_LOCAL_FONTS.values()), ""))

def _prepare_text(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))

def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str, bg_mode: str = "transparent", bg_photo: Optional[bytes] = None, as_webp: bool = False) -> bytes:
    MAX_DIM = 512
    W, H = MAX_DIM, MAX_DIM

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if bg_photo:
        try:
            bg_img = Image.open(BytesIO(bg_photo)).convert("RGBA")
            bg_img.thumbnail((W, H), Image.Resampling.LANCZOS)
            paste_x = (W - bg_img.width) // 2
            paste_y = (H - bg_img.height) // 2
            img.paste(bg_img, (paste_x, paste_y), bg_img)
        except Exception as e:
            print(f"Error processing background photo, falling back to transparent: {e}")
            pass
    elif bg_mode == "default":
        img = Image.new("RGBA", (W, H), (20, 20, 35, 255))

    draw = ImageDraw.Draw(img)
    color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    padding = 40
    box_w, box_h = W - 2*padding, H - 2*padding
    base_size = {"small": 64, "medium": 96, "large": 128}.get(size_key, 96)
    font_path = resolve_font_path(font_key, text)
    txt = _prepare_text(text)

    size = base_size
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size)
            bbox = draw.textbbox((0,0), txt, font=font)
            if (bbox[2]-bbox[0] <= box_w) and (bbox[3]-bbox[1] <= box_h):
                break
        except Exception:
            break
        size -= 1

    font = ImageFont.truetype(font_path, size=size)
    bbox = draw.textbbox((0,0), txt, font=font)
    text_width, text_height = bbox[2]-bbox[0], bbox[3]-bbox[1]

    y = {"top": padding, "bottom": H - padding - text_height}.get(v_pos, (H - text_height) / 2)
    x = {"left": padding, "right": W - padding - text_width}.get(h_pos, W / 2)
    anchor = "mm" if h_pos == "center" else "lm"
    draw.text((x, y), txt, font=font, fill=color, anchor=anchor, stroke_width=2, stroke_fill=(0,0,0,220))

    buf = BytesIO()
    if as_webp:
        img.save(buf, format="WEBP", quality=90)
    else:
        img.save(buf, format="PNG", optimize=True, compress_level=9)

    result = buf.getvalue()

    if not as_webp and len(result) > 64 * 1024:
        try:
            quantized_img = img.quantize(colors=256, dither=Image.Dither.NONE).convert("RGBA")
            buf2 = BytesIO()
            quantized_img.save(buf2, format="PNG", optimize=True, compress_level=9)
            new_result = buf2.getvalue()
            if len(new_result) < len(result):
                result = new_result
        except Exception as e:
            print(f"Could not quantize image: {e}")

    return result
