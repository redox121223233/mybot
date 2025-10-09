#!/usr/bin/env python3
"""
تست ترتیب چینش کلمات فارسی
"""

import sys
sys.path.insert(0, '.')

from PIL import Image, ImageDraw, ImageFont
from bot import _prepare_text, _detect_language, wrap_text_to_width, resolve_font_path

def test_persian_word_order():
    """تست ترتیب کلمات در متن فارسی"""
    print("=" * 60)
    print("تست ترتیب کلمات فارسی")
    print("=" * 60)
    
    # متن فارسی با ترتیب مشخص
    test_texts = [
        "سلام دنیا",
        "این یک متن فارسی است",
        "ربات استیکر ساز REDOX",
        "چطورید دوستان عزیز",
    ]
    
    # ایجاد تصویر و فونت
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = resolve_font_path("Default", "متن تست")
    font = ImageFont.truetype(font_path, size=48) if font_path else ImageFont.load_default()
    
    max_width = 300  # محدودیت عرض برای تست
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n{i}. متن: {text}")
        
        # تشخیص زبان
        lang = _detect_language(text)
        print(f"   زبان: {lang}")
        
        # آماده‌سازی متن
        prepared = _prepare_text(text)
        print(f"   آماده‌شده: {prepared}")
        
        # چینش متن
        lines = wrap_text_to_width(draw, prepared, font, max_width)
        print(f"   تعداد خطوط: {len(lines)}")
        
        print("   خطوط (از بالا به پایین):")
        for j, line in enumerate(lines, 1):
            print(f"     خط {j}: {line}")
            # نمایش ترتیب کلمات در هر خط
            words = line.split()
            print(f"        کلمات: {' → '.join(words)}")
        
        # بررسی ترتیب کلی
        all_words = []
        for line in lines:
            all_words.extend(line.split())
        print(f"   ترتیب کلی کلمات: {' → '.join(all_words)}")
        
        # آیا ترتیب درست است؟
        original_words = text.split()
        if lang == "persian":
            # برای فارسی، انتظار داریم کلمات درست چیده شوند
            print(f"   ✓ ترتیب اصلی: {' → '.join(original_words)}")
            print(f"   ✓ ترتیب نهایی: {' → '.join(all_words)}")
            
            # بررسی اینکه آیا ترتیب حفظ شده است
            if len(original_words) == len(all_words):
                print("   ✅ تعداد کلمات درست است")
            else:
                print("   ⚠️ تعداد کلمات متفاوت است")

def test_long_persian_text():
    """تست متن فارسی بلند"""
    print("\n" + "=" * 60)
    print("تست متن فارسی بلند - بررسی ترتیب خطوط")
    print("=" * 60)
    
    # متن فارسی بلند
    long_text = "این یک متن بلند فارسی است که باید به درستی در چند خط چیده شود"
    
    print(f"متن اصلی: {long_text}")
    print(f"کلمات اصلی: {' → '.join(long_text.split())}")
    
    # آماده‌سازی
    prepared = _prepare_text(long_text)
    lang = _detect_language(prepared)
    
    print(f"\nزبان: {lang}")
    print(f"متن آماده‌شده: {prepared}")
    
    # ایجاد تصویر و فونت
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = resolve_font_path("Default", prepared)
    font = ImageFont.truetype(font_path, size=36) if font_path else ImageFont.load_default()
    
    # چینش متن با عرض‌های مختلف
    for width in [200, 300, 400]:
        print(f"\n--- عرض: {width}px ---")
        lines = wrap_text_to_width(draw, prepared, font, width)
        
        print(f"تعداد خطوط: {len(lines)}")
        print("خطوط از بالا به پایین:")
        
        for i, line in enumerate(lines, 1):
            print(f"  خط {i}: {line}")
            words = line.split()
            print(f"     کلمات: {' → '.join(words)}")
        
        # بررسی ترتیب کلی
        all_words = []
        for line in lines:
            all_words.extend(line.split())
        print(f"ترتیب کلی: {' → '.join(all_words)}")

if __name__ == "__main__":
    try:
        test_persian_word_order()
        test_long_persian_text()
        
        print("\n" + "=" * 60)
        print("✅ تست‌های ترتیب کلمات انجام شد")
        print("📋 نتیجه: بررسی کنید که آیا ترتیب کلمات درست است؟")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)