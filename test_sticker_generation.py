#!/usr/bin/env python3
import os
import sys
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Import the actual rendering function from bot.py
def _prepare_text(text):
    """Prepare text for rendering (same as bot.py)"""
    if not text:
        return ""
    
    # Use arabic_reshaper for proper Persian text rendering
    reshaped_text = arabic_reshaper.reshape(text.strip())
    bidi_text = get_display(reshaped_text)
    
    return bidi_text

def resolve_font_path(font_key=None, text=""):
    """Font resolution logic from bot.py"""
    FONT_DIR = "./fonts"
    
    LOCAL_FONT_FILES = {
        "Vazirmatn": ["Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf"],
        "NotoNaskh": ["NotoNaskhArabic-Regular.ttf", "NotoNaskhArabic-Medium.ttf"],
        "Sahel": ["Sahel.ttf", "Sahel-Bold.ttf"],
        "IRANSans": ["IRANSans.ttf", "IRANSansX-Regular.ttf"],
        "Roboto": ["Roboto-Regular.ttf", "Roboto-Medium.ttf"],
        "Default": ["Vazirmatn-Regular.ttf", "Roboto-Regular.ttf"],
    }
    
    PERSIAN_FONTS = ["Vazirmatn", "NotoNaskh", "Sahel", "IRANSans"]
    ENGLISH_FONTS = ["Roboto"]
    
    # Load available fonts
    _LOCAL_FONTS = {}
    if os.path.isdir(FONT_DIR):
        for logical, names in LOCAL_FONT_FILES.items():
            for name in names:
                p = os.path.join(FONT_DIR, name)
                if os.path.isfile(p):
                    _LOCAL_FONTS[logical] = p
                    break
    
    # If specific font requested and available
    if font_key and font_key in _LOCAL_FONTS:
        return _LOCAL_FONTS[font_key]
    
    # Auto-detect language and select font
    if text:
        # Detect language
        persian_chars = 0
        english_chars = 0
        for char in text:
            if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
                persian_chars += 1
            elif ('a' <= char.lower() <= 'z'):
                english_chars += 1
        
        total_chars = persian_chars + english_chars
        if total_chars > 0 and persian_chars / total_chars > 0.3:
            # Persian text - use Persian fonts
            for font_name in PERSIAN_FONTS:
                if font_name in _LOCAL_FONTS:
                    return _LOCAL_FONTS[font_name]
        else:
            # English text - use English fonts
            for font_name in ENGLISH_FONTS:
                if font_name in _LOCAL_FONTS:
                    return _LOCAL_FONTS[font_name]
    
    # Fallback to first available font
    return next(iter(_LOCAL_FONTS.values()), "")

def render_sticker_image(text, position="center", font_key=None, color_hex="#FFFFFF", size_key="medium"):
    """Test the actual sticker rendering logic"""
    W, H = 512, 512
    
    # Create transparent background
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Parse color
    color_hex = (color_hex or "#ffffff").strip().lstrip("#")
    if len(color_hex) == 3:
        r, g, b = [int(c * 2, 16) for c in color_hex]
    else:
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
    color = (r, g, b, 255)
    
    padding = 28
    box_w, box_h = W - 2 * padding, H - 2 * padding
    
    # Font size mapping
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)
    
    # Get font path
    font_path = resolve_font_path(font_key, text)
    print(f"Using font: {font_path}")
    
    try:
        font = ImageFont.truetype(font_path, size=base_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    # Prepare text
    txt = _prepare_text(text)
    print(f"Prepared text: {txt}")
    
    # Determine if text is Persian for alignment
    is_persian = False
    for char in text:
        if '\u0600' <= char <= '\u06FF':
            is_persian = True
            break
    
    # Position and alignment
    if is_persian:
        # Right-to-left alignment for Persian
        align = "right"
        if position == "top":
            x, y, anchor = W - padding, padding, "rt"
        elif position == "bottom":
            x, y, anchor = W - padding, H - padding, "rb"
        else:  # center
            x, y, anchor = W - padding, H / 2, "rm"
    else:
        # Left-to-right alignment for English
        align = "left"
        if position == "top":
            x, y, anchor = padding, padding, "lt"
        elif position == "bottom":
            x, y, anchor = padding, H - padding, "lb"
        else:  # center
            x, y, anchor = W / 2, H / 2, "mm"
            align = "center"
    
    # Draw text with stroke
    draw.multiline_text(
        (x, y),
        txt,
        font=font,
        fill=color,
        anchor=anchor,
        align=align,
        spacing=6,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 220)
    )
    
    # Save as PNG
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_sticker_generation():
    """Test sticker generation with various Persian texts"""
    test_cases = [
        {"text": "سلام دنیا", "font": "Vazirmatn", "position": "center"},
        {"text": "خوش آمدید", "font": "Sahel", "position": "top"},
        {"text": "تست فونت", "font": "IRANSans", "position": "bottom"},
        {"text": "Hello World", "font": "Roboto", "position": "center"},
        {"text": "سلام Hello", "font": None, "position": "center"},  # Auto-detect
    ]
    
    for i, case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Text: {case['text']}")
        print(f"Font: {case['font']}")
        print(f"Position: {case['position']}")
        
        try:
            sticker_bytes = render_sticker_image(
                text=case['text'],
                position=case['position'],
                font_key=case['font'],
                color_hex="#FFFFFF",
                size_key="medium"
            )
            
            # Save the sticker
            filename = f"sticker_test_{i+1}.png"
            with open(filename, 'wb') as f:
                f.write(sticker_bytes)
            
            print(f"✅ Successfully generated: {filename}")
            
        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    print("=== Testing Sticker Generation ===")
    test_sticker_generation()
    print("\n=== Test Complete ===")