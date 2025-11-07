#!/usr/bin/env python3
"""
Fixed render_image function for WebP format
"""

import os
import io
import logging
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

logger = logging.getLogger(__name__)

def _parse_hex(hx: str) -> tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3:
        r, g, b = [int(c * 2, 16) for c in hx]
    else:
        r = int(hx[0:2], 16)
        g = int(hx[2:4], 16)
        b = int(hx[4:6], 16)
    return (r, g, b, 255)

def _prepare_text(text: str) -> str:
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def resolve_font_path(font_key: str, text: str = "") -> str:
    FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
    LOCAL_FONT_FILES = {
        "Vazirmatn": "Vazirmatn-Regular.ttf",
        "Sahel": "Sahel.ttf",
        "IRANSans": "IRANSans.ttf",
        "Roboto": "Roboto-Regular.ttf",
        "Default": "Vazirmatn-Regular.ttf",
    }
    
    _LOCAL_FONTS = {
        key: os.path.join(FONT_DIR, path)
        for key, path in LOCAL_FONT_FILES.items()
        if os.path.isfile(os.path.join(FONT_DIR, path))
    }
    
    return _LOCAL_FONTS.get(font_key, _LOCAL_FONTS.get("Default", ""))

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    size = base
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h:
            return size
        size -= 1
    return max(size, 12)

async def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str, 
                      bg_mode: str = "transparent", bg_photo_path: str | None = None, 
                      for_telegram_pack: bool = False) -> bytes:
    """
    Enhanced render_image function with guaranteed WebP output
    """
    W, H = (512, 512)
    img = None
    
    try:
        logger.info(f"Rendering image with text: '{text}', for_telegram_pack: {for_telegram_pack}")
        
        if bg_photo_path and os.path.exists(bg_photo_path):
            try:
                img = Image.open(bg_photo_path).convert("RGBA").resize((W, H))
                logger.info(f"Successfully loaded background image from {bg_photo_path}")
            except Exception as e:
                logger.error(f"Failed to open or process image from path {bg_photo_path}: {e}", exc_info=True)
                img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        else:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0) if bg_mode == "transparent" else (255, 255, 255, 255))

        draw = ImageDraw.Draw(img)
        color = _parse_hex(color_hex)
        padding = 40
        box_w, box_h = W - 2 * padding, H - 2 * padding
        size_map = {"small": 64, "medium": 96, "large": 128}
        base_size = size_map.get(size_key, 96)

        font_path = resolve_font_path(font_key, text)
        txt = _prepare_text(text)
        final_size = fit_font_size(draw, txt, font_path, base_size, box_w, box_h)
        
        try:
            font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), txt, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if v_pos == "top": y = padding
        elif v_pos == "bottom": y = H - padding - text_height
        else: y = (H - text_height) / 2

        if h_pos == "left": x = padding
        elif h_pos == "right": x = W - padding - text_width
        else: x = W / 2

        draw.text((x, y), txt, font=font, fill=color, anchor="mm" if h_pos == "center" else "lm", 
                 stroke_width=2, stroke_fill=(0, 0, 0, 220))

        buf = io.BytesIO()
        
        # ALWAYS use WebP format with optimal settings for Telegram
        if for_telegram_pack:
            # Special settings for Telegram sticker packs
            img.save(buf, format='WEBP', quality=95, method=4, lossless=False)
            logger.info(f"Generated WebP sticker for Telegram pack, size: {len(buf.getvalue())} bytes")
        else:
            # Also use WebP for previews for consistency
            img.save(buf, format='WEBP', quality=92, method=6)
            logger.info(f"Generated WebP preview, size: {len(buf.getvalue())} bytes")
        
        result = buf.getvalue()
        
        # Verify it's actually WebP format
        if not result.startswith(b'RIFF') or b'WEBP' not in result[8:12]:
            logger.error("Generated image is not in WebP format!")
            # Force WebP conversion
            buf.seek(0)
            img.save(buf, format='WEBP', quality=90)
            result = buf.getvalue()
            logger.info(f"Force converted to WebP, size: {len(result)} bytes")
        
        return result
        
    finally:
        if bg_photo_path and os.path.exists(bg_photo_path):
            try:
                os.remove(bg_photo_path)
                logger.info(f"Successfully cleaned up temporary file: {bg_photo_path}")
            except Exception as e:
                logger.error(f"Failed to clean up temporary file {bg_photo_path}: {e}", exc_info=True)