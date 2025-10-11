#!/usr/bin/env python3
import os
import sys
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Test the actual rendering logic from bot.py
def _prepare_text(text):
    """Prepare text for rendering (same as bot.py)"""
    if not text:
        return ""
    
    # Use arabic_reshaper for proper Persian text rendering
    reshaped_text = arabic_reshaper.reshape(text.strip())
    bidi_text = get_display(reshaped_text)
    
    return bidi_text

def test_actual_rendering():
    """Test actual rendering with Persian text"""
    FONT_DIR = './fonts'
    
    # Test cases
    test_cases = [
        "سلام دنیا",
        "خوش آمدید",
        "تست فونت فارسی",
        "Hello World",
        "سلام Hello"
    ]
    
    for text in test_cases:
        print(f"\nTesting: {text}")
        
        # Detect language and select font
        persian_chars = 0
        english_chars = 0
        for char in text:
            if '\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or '\uFB50' <= char <= '\uFDFF' or '\uFE70' <= char <= '\uFEFF':
                persian_chars += 1
            elif ('a' <= char.lower() <= 'z'):
                english_chars += 1
        
        total_chars = persian_chars + english_chars
        if total_chars > 0 and persian_chars / total_chars > 0.3:
            font_name = 'Vazirmatn-Regular.ttf'
            print(f"  Using Persian font: {font_name}")
        else:
            font_name = 'Roboto-Regular.ttf'
            print(f"  Using English font: {font_name}")
        
        font_path = os.path.join(FONT_DIR, font_name)
        print(f"  Font path: {font_path}")
        
        try:
            font = ImageFont.truetype(font_path, size=48)
            prepared_text = _prepare_text(text)
            
            # Create test image
            img = Image.new('RGBA', (400, 100), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # Calculate text size for centering
            bbox = draw.textbbox((0, 0), prepared_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Center the text
            x = (400 - text_width) // 2
            y = (100 - text_height) // 2
            
            # Draw text
            draw.text((x, y), prepared_text, font=font, fill=(0, 0, 0, 255))
            
            # Save test image
            output_path = f"./test_output_{text.replace(' ', '_')[:10]}.png"
            img.save(output_path)
            print(f"  ✅ Successfully rendered: {output_path}")
            
        except Exception as e:
            print(f"  ❌ Failed: {e}")

if __name__ == "__main__":
    print("=== Testing Actual Persian Text Rendering ===")
    test_actual_rendering()
    print("\n=== Test Complete ===")