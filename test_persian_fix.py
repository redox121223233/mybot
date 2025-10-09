#!/usr/bin/env python3
"""
تست تابع _prepare_text برای اطمینان از عملکرد صحیح فونت فارسی
"""

import sys
sys.path.insert(0, '.')

# Import تابع‌های مورد نیاز از bot.py
from bot import _prepare_text, _detect_language

def test_persian_text():
    """تست متن فارسی"""
    print("=" * 50)
    print("تست متن فارسی")
    print("=" * 50)
    
    # تست متن‌های فارسی
    test_cases = [
        "سلام",
        "سلام دنیا",
        "استیکر ساز",
        "این یک متن فارسی است",
        "Hello World",  # انگلیسی
        "سلام Hello",  # ترکیبی
    ]
    
    for text in test_cases:
        lang = _detect_language(text)
        prepared = _prepare_text(text)
        print(f"\nمتن اصلی: {text}")
        print(f"زبان تشخیص داده شده: {lang}")
        print(f"متن پردازش شده: {prepared}")
        print(f"طول متن اصلی: {len(text)}, طول متن پردازش شده: {len(prepared)}")
        
        # بررسی اینکه متن خالی نباشد
        if text.strip() and not prepared:
            print("⚠️ خطا: متن پردازش شده خالی است!")
        else:
            print("✅ متن با موفقیت پردازش شد")

def test_quota_functions():
    """تست توابع محدودیت"""
    print("\n" + "=" * 50)
    print("تست توابع محدودیت")
    print("=" * 50)
    
    from bot import user, _quota_left_ai, _quota_left_simple, DAILY_LIMIT_AI, DAILY_LIMIT_SIMPLE
    
    # تست برای کاربر عادی
    test_user_id = 123456789
    u = user(test_user_id)
    
    print(f"\nکاربر جدید (ID: {test_user_id}):")
    print(f"  AI استفاده شده: {u.get('ai_used', 0)}")
    print(f"  Simple استفاده شده: {u.get('simple_used', 0)}")
    
    left_ai = _quota_left_ai(u, False)
    left_simple = _quota_left_simple(u, False)
    
    print(f"  سهمیه باقی‌مانده AI: {left_ai} از {DAILY_LIMIT_AI}")
    print(f"  سهمیه باقی‌مانده Simple: {left_simple} از {DAILY_LIMIT_SIMPLE}")
    
    if left_ai == DAILY_LIMIT_AI and left_simple == DAILY_LIMIT_SIMPLE:
        print("✅ محدودیت‌ها به درستی مقداردهی شدند")
    else:
        print("⚠️ خطا در مقداردهی محدودیت‌ها")
    
    # تست برای ادمین
    from bot import ADMIN_ID
    admin_u = user(ADMIN_ID)
    admin_left_ai = _quota_left_ai(admin_u, True)
    admin_left_simple = _quota_left_simple(admin_u, True)
    
    print(f"\nادمین (ID: {ADMIN_ID}):")
    print(f"  سهمیه باقی‌مانده AI: {admin_left_ai}")
    print(f"  سهمیه باقی‌مانده Simple: {admin_left_simple}")
    
    if admin_left_ai == 999999 and admin_left_simple == 999999:
        print("✅ ادمین نامحدود است")
    else:
        print("⚠️ خطا: ادمین باید نامحدود باشد")

if __name__ == "__main__":
    try:
        test_persian_text()
        test_quota_functions()
        print("\n" + "=" * 50)
        print("✅ تمام تست‌ها با موفقیت انجام شد!")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ خطا در اجرای تست: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)