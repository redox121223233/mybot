#!/usr/bin/env python3
"""
تست تابع wrap_text_to_width برای بررسی مشکل چینش متن فارسی
"""

import sys
sys.path.insert(0, '.')

from PIL import Image, ImageDraw, ImageFont
from bot import wrap_text_to_width, resolve_font_path, _prepare_text

def test_text_wrapping():
    """تست چینش متن فارسی"""
    print("=" * 60)
    print("تست چینش متن فارسی")
    print("=" * 60)
    
    # ایجاد یک تصویر تست
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # متن فارسی طولانی برای تست
    test_texts = [
        "سلام این یک متن فارسی برای تست چینش کلمات است",
        "این یک جمله بلند فارسی است که باید به درستی در چند خط چیده شود",
        "ربات استیکر ساز REDOX",
        "Hello World این یک متن ترکیبی است",
    ]
    
    # استفاده از فونت پیش‌فرض
    font_path = resolve_font_path("Default", test_texts[0])
    font = ImageFont.truetype(font_path, size=48) if font_path else ImageFont.load_default()
    
    max_width = 400  # عرض قابل استفاده
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n{i}. متن تست:")
        print(f"   متن اصلی: {text}")
        
        # آماده‌سازی متن (برای فارسی)
        prepared_text = _prepare_text(text)
        print(f"   متن آماده‌شده: {prepared_text}")
        
        # چینش متن
        lines = wrap_text_to_width(draw, prepared_text, font, max_width)
        print(f"   تعداد خطوط: {len(lines)}")
        
        for j, line in enumerate(lines, 1):
            print(f"   خط {j}: {line}")
        
        # بررسی ترتیب خطوط
        print(f"   ترتیب خطوط: {'بالا به پایین' if len(lines) > 1 else 'تک خطی'}")
        
        # تست visual (طول خطوط)
        for j, line in enumerate(lines):
            length = draw.textlength(line, font=font)
            print(f"   طول خط {j+1}: {length:.1f}px از {max_width}px")
            if length > max_width:
                print(f"   ⚠️ خط {j+1} از حد مجاز عریض‌تر است!")

def test_rtl_wrapping():
    """تست چینش RTL برای فارسی"""
    print("\n" + "=" * 60)
    print("تست چینش RTL")
    print("=" * 60)
    
    # متن فارسی برای تست RTL
    persian_text = "این یک متن فارسی است که باید از راست به چپ خوانده شود"
    prepared = _prepare_text(persian_text)
    
    print(f"متن فارسی: {persian_text}")
    print(f"متن آماده‌شده: {prepared}")
    print(f"ترتیب حروف: {'RTL' if any(ord(c) > 0x600 for c in prepared) else 'LTR'}")

if __name__ == "__main__":
    try:
        test_text_wrapping()
        test_rtl_wrapping()
        print("\n" + "=" * 60)
        print("✅ تست‌های چینش متن انجام شد")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)