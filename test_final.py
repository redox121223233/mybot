#!/usr/bin/env python3
"""
تست نهایی عملکرد ربات
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import render_image, _detect_language, resolve_font_path

def test_final():
    print("=== تست نهایی عملکرد ربات ===\n")
    
    # تست 1: متن فارسی
    persian_text = "سلام دنیا"
    print(f"1. متن فارسی: {persian_text}")
    lang = _detect_language(persian_text)
    font_path = resolve_font_path(None, persian_text)
    print(f"   زبان: {lang}")
    print(f"   فونت: {os.path.basename(font_path)}")
    
    try:
        img_bytes = render_image(
            text=persian_text,
            position="center",
            font_key=None,
            color_hex="#FFFFFF",
            size_key="large",
            bg_mode="transparent"
        )
        print(f"   رندر: ✅ ({len(img_bytes)} bytes)")
    except Exception as e:
        print(f"   رندر: ❌ {e}")
    
    # تست 2: متن انگلیسی
    english_text = "Hello World"
    print(f"\n2. متن انگلیسی: {english_text}")
    lang = _detect_language(english_text)
    font_path = resolve_font_path(None, english_text)
    print(f"   زبان: {lang}")
    print(f"   فونت: {os.path.basename(font_path)}")
    
    try:
        img_bytes = render_image(
            text=english_text,
            position="center",
            font_key=None,
            color_hex="#FFFFFF",
            size_key="large",
            bg_mode="transparent"
        )
        print(f"   رندر: ✅ ({len(img_bytes)} bytes)")
    except Exception as e:
        print(f"   رندر: ❌ {e}")
    
    print("\n✅ تست نهایی تمام شد!")

if __name__ == "__main__":
    test_final()