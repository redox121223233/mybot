#!/usr/bin/env python3
"""
تست کامل با متن‌های مختلف
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import render_image

test_cases = [
    ("سلام", "test_1_salam.png"),
    ("سلام دنیا", "test_2_salam_donya.png"),
    ("این یک متن فارسی طولانی است", "test_3_long_persian.png"),
    ("Hello", "test_4_hello.png"),
    ("Hello World", "test_5_hello_world.png"),
    ("This is a long English text", "test_6_long_english.png"),
    ("سلام Hello", "test_7_mixed.png"),
]

print("=== تست رندر با متن‌های مختلف ===\n")

for text, filename in test_cases:
    try:
        img_bytes = render_image(
            text=text,
            position="center",
            font_key=None,  # انتخاب خودکار
            color_hex="#FFFFFF",
            size_key="large",
            bg_mode="transparent"
        )
        
        with open(filename, "wb") as f:
            f.write(img_bytes)
        
        print(f"✅ {filename}: {text} ({len(img_bytes)} bytes)")
    except Exception as e:
        print(f"❌ {filename}: {text} - خطا: {e}")

print("\n✅ همه تست‌ها تمام شد!")