#!/usr/bin/env python3
# تست نهایی RTL برای متن فارسی

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import render_image, is_persian, _prepare_text

def test_rtl_final():
    """تست نهایی RTL برای متن فارسی"""
    print("🧪 تست نهایی RTL برای متن فارسی...")
    
    # تست تشخیص زبان
    test_cases = [
        ("سلام دنیا", True),
        ("Hello World", False),
        ("سلام World", True),
        ("123", False),
        ("متن فارسی و English", True),
    ]
    
    print("\n📋 تست تشخیص زبان:")
    for text, expected in test_cases:
        result = is_persian(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}' -> فارسی: {result}")
    
    # تست آماده‌سازی متن
    print("\n📋 تست آماده‌سازی متن:")
    persian_texts = [
        "سلام",
        "این یک متن فارسی است",
        "123 فارسی",
        "تست RTL"
    ]
    
    for text in persian_texts:
        prepared = _prepare_text(text)
        print(f"📄 '{text}' -> '{prepared}'")
    
    # تست رندر تصویر
    print("\n🎨 تست رندر تصویر:")
    try:
        # تست متن فارسی
        fa_image = render_image(
            text="سلام دنیا",
            position="center",
            font_key="Default",
            color_hex="#FFFFFF",
            size_key="medium",
            bg_mode="default"
        )
        print(f"✅ رندر فارسی: {len(fa_image)} بایت")
        
        # تست متن انگلیسی
        en_image = render_image(
            text="Hello World",
            position="center",
            font_key="Default",
            color_hex="#FFFFFF",
            size_key="medium",
            bg_mode="default"
        )
        print(f"✅ رندر انگلیسی: {len(en_image)} بایت")
        
        # ذخیره تصاویر برای بررسی
        with open("final_rtl_fa.png", "wb") as f:
            f.write(fa_image)
        with open("final_rtl_en.png", "wb") as f:
            f.write(en_image)
        
        print("📸 تصاویر تست ذخیره شدند: final_rtl_fa.png, final_rtl_en.png")
        
    except Exception as e:
        print(f"❌ خطا در رندر: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ تست نهایی RTL برای فارسی کامل شد!")

if __name__ == "__main__":
    test_rtl_final()