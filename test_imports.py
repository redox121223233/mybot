#!/usr/bin/env python3
"""
تست import ها و syntax کد
"""

import sys

def test_imports():
    """تست import های اصلی"""
    print("=" * 50)
    print("تست Import ها")
    print("=" * 50)
    
    try:
        print("\n✓ Import bot module...")
        import bot
        print("✅ bot module با موفقیت import شد")
        
        print("\n✓ بررسی توابع کلیدی...")
        required_functions = [
            '_prepare_text',
            '_detect_language',
            '_quota_left_ai',
            '_quota_left_simple',
            'user',
            'sess',
            'render_image',
        ]
        
        for func_name in required_functions:
            if hasattr(bot, func_name):
                print(f"  ✅ {func_name} موجود است")
            else:
                print(f"  ❌ {func_name} موجود نیست!")
                return False
        
        print("\n✓ بررسی متغیرهای کلیدی...")
        required_vars = [
            'DAILY_LIMIT_AI',
            'DAILY_LIMIT_SIMPLE',
            'BOT_TOKEN',
            'ADMIN_ID',
        ]
        
        for var_name in required_vars:
            if hasattr(bot, var_name):
                value = getattr(bot, var_name)
                print(f"  ✅ {var_name} = {value}")
            else:
                print(f"  ❌ {var_name} موجود نیست!")
                return False
        
        return True
        
    except Exception as e:
        print(f"\n❌ خطا در import: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_syntax():
    """تست syntax کد"""
    print("\n" + "=" * 50)
    print("تست Syntax")
    print("=" * 50)
    
    try:
        import py_compile
        print("\n✓ کامپایل bot.py...")
        py_compile.compile('bot.py', doraise=True)
        print("✅ bot.py بدون خطای syntax است")
        return True
    except Exception as e:
        print(f"\n❌ خطای syntax: {e}")
        return False

if __name__ == "__main__":
    print("\n🔍 شروع تست‌های کامل...\n")
    
    syntax_ok = test_syntax()
    imports_ok = test_imports()
    
    print("\n" + "=" * 50)
    print("نتیجه نهایی")
    print("=" * 50)
    
    if syntax_ok and imports_ok:
        print("\n✅ تمام تست‌ها با موفقیت انجام شد!")
        print("✅ کد آماده استفاده است")
        sys.exit(0)
    else:
        print("\n❌ برخی تست‌ها با خطا مواجه شدند")
        sys.exit(1)