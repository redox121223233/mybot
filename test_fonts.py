#!/usr/bin/env python3
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Add the current directory to path so we can import bot functions
sys.path.insert(0, os.path.dirname(__file__))

def test_font_loading():
    """Test if fonts are loading correctly"""
    FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
    print(f"Font directory: {FONT_DIR}")
    print(f"Directory exists: {os.path.isdir(FONT_DIR)}")
    
    LOCAL_FONT_FILES = {
        'Vazirmatn': ['Vazirmatn-Regular.ttf', 'Vazirmatn-Medium.ttf'],
        'NotoNaskh': ['NotoNaskhArabic-Regular.ttf', 'NotoNaskhArabic-Medium.ttf'],
        'Sahel': ['Sahel.ttf', 'Sahel-Bold.ttf'],
        'IRANSans': ['IRANSans.ttf', 'IRANSansX-Regular.ttf'],
        'Roboto': ['Roboto-Regular.ttf', 'Roboto-Medium.ttf'],
        'Default': ['Vazirmatn-Regular.ttf', 'Roboto-Regular.ttf'],
    }
    
    def _load_local_fonts():
        found = {}
        if os.path.isdir(FONT_DIR):
            for logical, names in LOCAL_FONT_FILES.items():
                for name in names:
                    p = os.path.join(FONT_DIR, name)
                    if os.path.isfile(p):
                        found[logical] = p
                        print(f'✅ Found {logical}: {p}')
                        break
                else:
                    print(f'❌ Missing {logical}: {names}')
        return found
    
    fonts = _load_local_fonts()
    print(f'\nLoaded fonts: {list(fonts.keys())}')
    return fonts

def test_persian_text_rendering():
    """Test rendering Persian text with available fonts"""
    fonts = test_font_loading()
    
    if not fonts:
        print("❌ No fonts available!")
        return
    
    # Test Persian text
    persian_text = "سلام دنیا"
    print(f"\nTesting Persian text: {persian_text}")
    
    # Prepare text (same as in bot.py)
    reshaped_text = arabic_reshaper.reshape(persian_text.strip())
    bidi_text = get_display(reshaped_text)
    print(f"Prepared text: {bidi_text}")
    
    # Test each available font
    for font_name, font_path in fonts.items():
        try:
            print(f"\nTesting font: {font_name}")
            font = ImageFont.truetype(font_path, size=48)
            
            # Create a small test image
            img = Image.new('RGBA', (200, 100), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Try to render the text
            draw.text((10, 10), bidi_text, font=font, fill=(255, 255, 255, 255))
            
            print(f"✅ {font_name} rendered successfully")
            
        except Exception as e:
            print(f"❌ {font_name} failed: {e}")

if __name__ == "__main__":
    print("=== Testing Font Loading ===")
    test_persian_text_rendering()
    print("\n=== Test Complete ===")