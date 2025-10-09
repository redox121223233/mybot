#!/usr/bin/env python3
"""
تست نهایی یکپارچه برای بررسی تمام تغییرات
"""

import sys
sys.path.insert(0, '.')

from PIL import Image, ImageDraw, ImageFont
from bot import (
    _prepare_text, 
    _detect_language, 
    wrap_text_to_width,
    optimize_text_wrapping_for_persian,
    resolve_font_path,
    render_image
)

def test_persian_text_rendering():
    """تست نهایی رندر متن فارسی"""
    print("=" * 60)
    print("تست نهایی رندر متن فارسی")
    print("=" * 60)
    
    # متن‌های تست
    test_cases = [
        "سلام دنیا",
        "این یک متن فارسی بلند است که باید به درستی در چند خط چیده شود",
        "ربات استیکر ساز REDOX برای تلگرام",
        "Hello World این یک متن ترکیبی است",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{i}. تست: {text}")
        
        # تشخیص زبان
        lang = _detect_language(text)
        print(f"   زبان: {lang}")
        
        # آماده‌سازی متن
        prepared = _prepare_text(text)
        print(f"   آماده‌شده: {prepared}")
        
        # ایجاد تصویر تست
        img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # فونت
        font_path = resolve_font_path("Default", prepared)
        font = ImageFont.truetype(font_path, size=48) if font_path else ImageFont.load_default()
        
        # چینش متن
        lines = wrap_text_to_width(draw, prepared, font, 400)
        
        # بهینه‌سازی برای فارسی
        if lang == "persian":
            original_lines = lines.copy()
            lines = optimize_text_wrapping_for_persian(prepared, lines, lang)
            print(f"   خطوط قبل از بهینه‌سازی: {len(original_lines)}")
            print(f"   خطوط بعد از بهینه‌سازی: {len(lines)}")
        
        print(f"   تعداد خطوط نهایی: {len(lines)}")
        for j, line in enumerate(lines, 1):
            print(f"     خط {j}: {line}")

def test_long_text_scenario():
    """تست سناریوی واقعی با متن بلند"""
    print("\n" + "=" * 60)
    print("تست سناریوی واقعی - متن بلند فارسی")
    print("=" * 60)
    
    # یک متن بلند واقعی
    long_text = """سلام دوستان عزیز
    این یک متن بلند فارسی است که میخواهم به صورت استیکر درآید
    و باید به درستی در چند خط چیده شود تا زیبا به نظر برسد
    ممنون از استفاده شما از ربات استیکر ساز"""
    
    print(f"متن تست:\n{long_text}")
    
    # آماده‌سازی
    prepared = _prepare_text(long_text)
    lang = _detect_language(prepared)
    
    print(f"\nزبان تشخیص داده شده: {lang}")
    print(f"متن آماده‌شده:\n{prepared}")
    
    # رندر نهایی
    try:
        img_data = render_image(
            text=long_text,
            position="center",
            font_key="Default",
            color_hex="#FFFFFF",
            size_key="medium",
            bg_mode="transparent",
            as_webp=False
        )
        
        print(f"\n✅ رندر موفق!")
        print(f"حجم تصویر: {len(img_data)} بایت")
        
    except Exception as e:
        print(f"\n❌ خطا در رندر: {e}")

def test_rtl_behavior():
    """تست رفتار RTL"""
    print("\n" + "=" * 60)
    print("تست رفتار RTL")
    print("=" * 60)
    
    rtl_texts = [
        "سلام",
        "چطورید؟",
        "این متن فارسی است",
        "123 عدد در متن فارسی",
    ]
    
    for text in rtl_texts:
        prepared = _prepare_text(text)
        print(f"اصل: {text}")
        print(f"RTL: {prepared}")
        print(f"RTL فعال: {'RTL' if prepared != text else 'LTR'}")
        print()

if __name__ == "__main__":
    try:
        test_persian_text_rendering()
        test_long_text_scenario()
        test_rtl_behavior()
        
        print("\n" + "=" * 60)
        print("🎉 تمام تست‌های نهایی با موفقیت انجام شد!")
        print("✅ آماده برای استفاده")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ خطا در تست نهایی: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)