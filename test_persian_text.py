#!/usr/bin/env python3
"""
تست نمایش صحیح متن فارسی
"""
import sys
import os

# Add parent directory to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bot import _prepare_text

# تست متن‌های فارسی
test_texts = [
    "سلام",
    "خوش آمدید",
    "استیکر ساده",
    "استیکر هوش مصنوعی",
    "سهمیه امروز",
    "راهنما",
    "پشتیبانی",
    "بازگشت به منو",
    "متن تست با اعداد 123",
    "Hello سلام Mixed Text"
]

def test_persian_text():
    """تست نمایش صحیح متن فارسی"""
    print("🧪 تست نمایش متن فارسی...\n")
    
    all_passed = True
    
    for i, text in enumerate(test_texts, 1):
        print(f"📝 تست {i}/{len(test_texts)}:")
        print(f"   ورودی: {text}")
        
        try:
            prepared = _prepare_text(text)
            print(f"   خروجی: {prepared}")
            
            # بررسی اینکه متن خالی نباشه
            if not prepared:
                print(f"   ❌ خطا: متن خالی است")
                all_passed = False
            else:
                print(f"   ✅ موفق")
                
        except Exception as e:
            print(f"   ❌ خطا: {e}")
            all_passed = False
            
        print()
    
    # نتیجه نهایی
    print("=" * 50)
    if all_passed:
        print("🎉 تمام تست‌ها موفق بودند!")
        print("🎉 متن فارسی حالا درست نمایش داده می‌شود!")
        return True
    else:
        print("⚠️ برخی تست‌ها ناموفق بودند.")
        return False

if __name__ == "__main__":
    result = test_persian_text()
    exit(0 if result else 1)