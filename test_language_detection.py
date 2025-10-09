#!/usr/bin/env python3
"""
تست تشخیص زبان و انتخاب فونت
"""
import sys
import os

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.dirname(__file__))

from bot import _detect_language, resolve_font_path, _LOCAL_FONTS

def test_language_detection():
    """تست تابع تشخیص زبان"""
    print("=== تست تشخیص زبان ===\n")
    
    test_cases = [
        ("سلام دنیا", "persian"),
        ("Hello World", "english"),
        ("این یک متن فارسی است", "persian"),
        ("This is an English text", "english"),
        ("سلام Hello", "persian"),  # ترکیبی با اکثریت فارسی
        ("Hello سلام", "english"),  # ترکیبی با اکثریت انگلیسی
        ("123456", "english"),  # فقط اعداد
        ("", "english"),  # متن خالی
    ]
    
    for text, expected in test_cases:
        result = _detect_language(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} متن: '{text}' -> زبان: {result} (انتظار: {expected})")

def test_font_selection():
    """تست انتخاب فونت"""
    print("\n=== تست انتخاب فونت ===\n")
    
    print("فونت‌های موجود:")
    for name, path in _LOCAL_FONTS.items():
        print(f"  - {name}: {os.path.basename(path)}")
    
    print("\nتست انتخاب فونت بر اساس زبان:")
    
    test_cases = [
        ("سلام دنیا", None),
        ("Hello World", None),
        ("این یک متن فارسی است", None),
        ("This is an English text", None),
    ]
    
    for text, font_key in test_cases:
        lang = _detect_language(text)
        font_path = resolve_font_path(font_key, text)
        font_name = os.path.basename(font_path) if font_path else "None"
        print(f"متن: '{text}' -> زبان: {lang} -> فونت: {font_name}")

if __name__ == "__main__":
    test_language_detection()
    test_font_selection()
    print("\n✅ تست‌ها با موفقیت اجرا شدند!")