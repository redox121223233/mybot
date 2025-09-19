# mybot/services/ai_manager.py
import os
import re
from PIL import Image, ImageDraw, ImageFont
from utils.logger import logger

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

# helper: load font (falls back to default)
def load_font(name="arial", size=40, bold=False):
    # map common names to files (you should place fonts in mybot/fonts/)
    name_lower = name.lower()
    candidates = []
    if "vazir" in name_lower:
        candidates = ["vazir.ttf", "vazir-bold.ttf"]
    elif "arial" in name_lower:
        candidates = ["arial.ttf", "arialbd.ttf", "Arial.ttf", "Arial Bold.ttf"]
    else:
        candidates = [f"{name}.ttf", f"{name}-bold.ttf", f"{name}.ttf"]

    # choose bold if requested
    if bold:
        candidates = [c for c in candidates if "bold" in c.lower() or "bd" in c.lower()] + candidates

    for c in candidates:
        path = os.path.join(FONTS_DIR, c)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue

    # fallback: default PIL font (not ideal for Persian)
    logger.warning("Font not found (%s). Using default font.", name)
    return ImageFont.load_default()

# simple instruction parser
def parse_instructions(text: str):
    """
    returns dict: {text, position, color, font, size, bold}
    position: one of top-left, top-right, top-center, center, bottom-left, bottom-right, bottom-center
    color: name or hex
    """
    # defaults
    result = {
        "text": text.strip(),
        "position": "center",
        "color": "white",
        "font": "arial",
        "size": 40,
        "bold": False
    }

    # try key:value lines
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # if looks like key:value pairs
    kv_like = any(":" in ln for ln in lines)
    if kv_like:
        for ln in lines:
            if ":" not in ln:
                continue
            k, v = ln.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if k in ("متن", "text"):
                result["text"] = v
            elif k in ("موقعیت", "position", "pos"):
                result["position"] = v.replace(" ", "-").lower()
            elif k in ("رنگ", "color"):
                result["color"] = v
            elif k in ("فونت", "font"):
                result["font"] = v
            elif k in ("اندازه", "size"):
                try:
                    result["size"] = int(re.findall(r"\d+", v)[0])
                except Exception:
                    pass
            elif k in ("bold", "بولد", "درشت"):
                result["bold"] = v.lower() in ("yes", "y", "true", "1", "بله", "yes", "y", "true")
    else:
        # try semicolon separated: "text; pos=bottom-center; color=#fff; size=40; bold"
        parts = re.split(r"[;|,]", text)
        if len(parts) > 1:
            # first part is text if doesn't contain =
            first = parts[0].strip()
            if "=" not in first:
                result["text"] = first
            for p in parts[1:]:
                p = p.strip()
                if not p: continue
                if "=" in p:
                    k, v = p.split("=", 1)
                    k = k.strip().lower()
                    v = v.strip()
                    if k in ("pos", "position"):
                        result["position"] = v
                    elif k in ("color",):
                        result["color"] = v
                    elif k in ("size",):
                        try:
                            result["size"] = int(re.findall(r"\d+", v)[0])
                        except:
                            pass
                    elif k in ("font",):
                        result["font"] = v
                else:
                    if p.lower() in ("bold", "بولد", "b"):
                        result["bold"] = True

    return result

# map position to coordinates
def _calc_position(img_size, text_size, position):
    W, H = img_size
    tw, th = text_size
    pos = position.lower()
    margin = int(min(W, H) * 0.03)  # 3% margin
    if pos in ("top-left", "topleft", "top left"):
        return (margin, margin)
    if pos in ("top-right", "topright", "top right"):
        return (W - tw - margin, margin)
    if pos in ("top-center", "topcenter", "top center"):
        return ((W - tw)//2, margin)
    if pos in ("bottom-left", "bottomleft", "bottom left"):
        return (margin, H - th - margin)
    if pos in ("bottom-right", "bottomright", "bottom right"):
        return (W - tw - margin, H - th - margin)
    if pos in ("bottom-center", "bottomcenter", "bottom center"):
        return ((W - tw)//2, H - th - margin)
    # center (default)
    return ((W - tw)//2, (H - th)//2)

# color normalization (accept names and hex)
def _normalize_color(c):
    c = (c or "white").strip()
    # if hex
    if re.match(r"^#?[0-9a-fA-F]{6}$", c):
        if not c.startswith("#"): c = "#" + c
        return c
    # basic names mapping (extendable)
    names = {
        "white":"#ffffff", "black":"#000000", "red":"#ff0000", "green":"#00ff00",
        "blue":"#0000ff", "yellow":"#ffff00", "orange":"#ff8800"
    }
    return names.get(c.lower(), c)

def render_text_on_image(input_path, output_path, instructions_text):
    """
    Read input image, parse instructions_text, render text, save output_path (PNG/WebP).
    Returns output_path.
    """
    ins = parse_instructions(instructions_text)
    text = ins["text"] or ""
    position = ins["position"]
    color = _normalize_color(ins["color"])
    font_name = ins["font"]
    size = ins["size"] or 40
    bold = ins["bold"]

    logger.info("AI render instructions: %s", ins)

    im = Image.open(input_path).convert("RGBA")
    txt_layer = Image.new("RGBA", im.size, (255,255,255,0))
    draw = ImageDraw.Draw(txt_layer)

    # load font
    font = load_font(font_name, size=size, bold=bold)

    # For multi-line text, wrap if needed
    # simple wrapping: splitlines and draw each line with small spacing
    lines = text.splitlines() if "\n" in text else [text]
    # measure combined size
    line_heights = []
    max_width = 0
    for l in lines:
        w,h = draw.textsize(l, font=font)
        line_heights.append((w,h))
        if w > max_width: max_width = w
    total_h = sum(h for _,h in line_heights) + (len(lines)-1) * int(size * 0.15)

    # compute top-left of first line (for positioned block)
    tw = max_width
    th = total_h
    base_x, base_y = _calc_position(im.size, (tw, th), position)

    # draw each line
    cur_y = base_y
    for idx, l in enumerate(lines):
        w,h = line_heights[idx]
        # align each line horizontally within block (left)
        x = base_x
        y = cur_y
        # draw shadow for readability
        shadow_color = "#000000"
        draw.text((x+2,y+2), l, font=font, fill=shadow_color)
        draw.text((x,y), l, font=font, fill=color)
        cur_y += h + int(size * 0.15)

    # composite
    out = Image.alpha_composite(im, txt_layer).convert("RGB")

    # save as webp (good for stickers) or png
    out_ext = os.path.splitext(output_path)[1].lower()
    try:
        if out_ext in (".webp",):
            out.save(output_path, format="WEBP", lossless=True, quality=95)
        else:
            out.save(output_path, format="PNG")
    except Exception as e:
        logger.exception("Failed to save rendered image: %s", e)
        out.save(output_path, format="PNG")

    return output_path
