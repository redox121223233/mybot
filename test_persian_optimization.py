#!/usr/bin/env python3
"""
تست بهینه‌سازی چینش متن برای فارسی
"""

import sys
sys.path.insert(0, '.')

from PIL import Image, ImageDraw, ImageFont
from bot import (
    wrap_text_to_width, 
    optimize_text_wrapping_for_persian, 
    resolve_font_path, 
    _prepare_text, 
    _detect_language
)

def test_persian_optimization():
    """تست بهینه‌سازی چینش برای متن فارسی"""
    print("=" * 60)
    print("تست بهینه‌سازی چینش متن فارسی")
    print("=" * 60)
    
    # ایجاد تصویر تست
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # متن فارسی طولانی برای تست
    test_cases = [
        {
            "text": "سلام این یک متن فارسی برای تست چینش کلمات است",
            "description": "متن فارسی ساده"
        },
        {
            "text": "این یک جمله بلند فارسی است که باید به درستی در چند خط چیده شود تا زیبا به نظر برسد",
            "description": "جمله بلند فارسی"
        },
        {
            "text": "ربات استیکر ساز REDOX برای تلگرام",
            "description": "متن ترکیبی فارسی-انگلیسی"
        }
    ]
    
    # استفاده از فونت پیش‌فرض
    font_path = resolve_font_path("Default", "متن تست")
    font = ImageFont.truetype(font_path, size=48) if font_path else ImageFont.load_default()
    
    max_width = 400
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}:")
        print(f"   متن اصلی: {test_case['text']}")
        
        # تشخیص زبان
        lang = _detect_language(test_case['text'])
        print(f"   زبان تشخیص داده شده: {lang}")
        
        # آماده‌سازی متن
        prepared_text = _prepare_text(test_case['text'])
        print(f"   متن آماده‌شده: {prepared_text}")
        
        # چینش متن
        lines = wrap_text_to_width(draw, prepared_text, font, max_width)
        print(f"   تعداد خطوط قبل از بهینه‌سازی: {len(lines)}")
        
        # بهینه‌سازی برای فارسی
        if lang == "persian":
            optimized_lines = optimize_text_wrapping_for_persian(prepared_text, lines, lang)
            print(f"   تعداد خطوط بعد از بهینه‌سازی: {len(optimized_lines)}")
            
            print("   خطوط بهینه‌شده:")
            for j, line in enumerate(optimized_lines, 1):
                print(f"     خط {j}: {line}")
                length = draw.textlength(line, font=font)
                print(f"       طول: {length:.1f}px")
        else:
            print("   خطوط:")
            for j, line in enumerate(lines, 1):
                print(f"     خط {j}: {line}")
                length = draw.textlength(line, font=font)
                print(f"       طول: {length:.1f}px")

def test_long_persian_text():
    """تست متن فارسی بلند"""
    print("\n" + "=" * 60)
    print("تست متن فارسی بلند")
    print("=" * 60)
    
    # متن فارسی بلند
    long_text = """سلام دوستان عزیز این یک متن بلند فارسی است 
    که میخواهم به صورت استیکر درآید و باید به درستی 
    در چند خط چیده شود تا زیبا به نظر برسد"""
    
    print(f"متن بلند فارسی:")
    print(f"{long_text}")
    
    # آماده‌سازی و چینش
    prepared = _prepare_text(long_text)
    lang = _detect_language(prepared)
    
    print(f"\nزبان: {lang}")
    print(f"متن آماده‌شده: {prepared}")
    
    # ایجاد تصویر و فونت
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = resolve_font_path("Default", prepared)
    font = ImageFont.truetype(font_path, size=36) if font_path else ImageFont.load_default()
    
    # چینش متن
    lines = wrap_text_to_width(draw, prepared, font, 350)
    
    if lang == "persian":
        lines = optimize_text_wrapping_for_persian(prepared, lines, lang)
    
    print(f"\nنتیجه نهایی ({len(lines)} خط):")
    for i, line in enumerate(lines, 1):
        print(f"خط {i}: {line}")

if __name__ == "__main__":
    try:
        test_persian_optimization()
        test_long_persian_text()
        print("\n" + "=" * 60)
        print("✅ تمام تست‌های بهینه‌سازی انجام شد")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)