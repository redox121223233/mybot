#!/usr/bin/env python3
"""
تست واقعی رندر کردن تصویر با متن فارسی و انگلیسی
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import render_image, _detect_language, resolve_font_path, _LOCAL_FONTS

def test_render():
    print("=== تست رندر تصویر ===\n")
    
    # تست متن فارسی
    persian_text = "سلام دنیا"
    print(f"متن فارسی: {persian_text}")
    lang = _detect_language(persian_text)
    print(f"زبان تشخیص داده شده: {lang}")
    font_path = resolve_font_path(None, persian_text)
    print(f"فونت انتخاب شده: {font_path}")
    print(f"فونت موجود است: {os.path.exists(font_path)}")
    
    try:
        img_bytes = render_image(
            text=persian_text,
            position="center",
            font_key=None,  # بدون مشخص کردن فونت
            color_hex="#FFFFFF",
            size_key="large",
            bg_mode="transparent"
        )
        print(f"✅ رندر موفق - حجم: {len(img_bytes)} bytes")
        
        # ذخیره تصویر
        with open("test_persian.png", "wb") as f:
            f.write(img_bytes)
        print("✅ تصویر ذخیره شد: test_persian.png\n")
    except Exception as e:
        print(f"❌ خطا در رندر: {e}\n")
    
    # تست متن انگلیسی
    english_text = "Hello World"
    print(f"متن انگلیسی: {english_text}")
    lang = _detect_language(english_text)
    print(f"زبان تشخیص داده شده: {lang}")
    font_path = resolve_font_path(None, english_text)
    print(f"فونت انتخاب شده: {font_path}")
    print(f"فونت موجود است: {os.path.exists(font_path)}")
    
    try:
        img_bytes = render_image(
            text=english_text,
            position="center",
            font_key=None,  # بدون مشخص کردن فونت
            color_hex="#FFFFFF",
            size_key="large",
            bg_mode="transparent"
        )
        print(f"✅ رندر موفق - حجم: {len(img_bytes)} bytes")
        
        # ذخیره تصویر
        with open("test_english.png", "wb") as f:
            f.write(img_bytes)
        print("✅ تصویر ذخیره شد: test_english.png\n")
    except Exception as e:
        print(f"❌ خطا در رندر: {e}\n")

if __name__ == "__main__":
    print("فونت‌های موجود:")
    for name, path in _LOCAL_FONTS.items():
        print(f"  {name}: {os.path.basename(path)}")
    print()
    
    test_render()