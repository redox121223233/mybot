#!/usr/bin/env python3
"""
تست API ربات در محیط محلی
"""
import asyncio
import os
from bot import render_image, _add_to_pack, user, sess

async def test_bot_functions():
    """تست توابع اصلی ربات"""
    print("🤖 تست توابع اصلی ربات...")
    
    # تست تولید استیکر
    print("\n📝 تست تولید استیکر فارسی...")
    try:
        sticker_bytes = render_image(
            text="سلام! این یک تست است",
            position="center",
            font_key="Vazirmatn",
            color_hex="#FFFFFF",
            size_key="medium",
            bg_mode="transparent"
        )
        
        with open('api_test_sticker.png', 'wb') as f:
            f.write(sticker_bytes)
        
        print("✅ استیکر تولید شد")
        print(f"   اندازه: {len(sticker_bytes)} بایت")
        
        # تبدیل به WebP برای تلگرام
        from PIL import Image
        from io import BytesIO
        
        img = Image.open(BytesIO(sticker_bytes))
        webp_buffer = BytesIO()
        img.save(webp_buffer, format='WEBP')
        webp_bytes = webp_buffer.getvalue()
        
        with open('api_test_sticker.webp', 'wb') as f:
            f.write(webp_bytes)
        
        print("✅ تبدیل به WebP موفق")
        print(f"   اندازه WebP: {len(webp_bytes)} بایت")
        
    except Exception as e:
        print(f"❌ خطا در تولید استیکر: {e}")
        import traceback
        traceback.print_exc()

def test_user_management():
    """تست مدیریت کاربران"""
    print("\n👤 تست مدیریت کاربران...")
    
    test_user_id = 123456789
    
    # ایجاد کاربر تست
    u = user(test_user_id)
    s = sess(test_user_id)
    
    print(f"✅ کاربر ایجاد شد: {test_user_id}")
    print(f"   سهمیه: {u.get('ai_used', 0)}")
    print(f"   حالت: {s.get('mode', 'نامشخص')}")
    
    # تست تنظیم پک
    u['pack'] = {
        'title': 'پک تست فارسی',
        'name': 'test_persian_pack',
        'created': False
    }
    
    print("✅ اطلاعات پک تنظیم شد")

def test_text_processing():
    """تست پردازش متن فارسی"""
    print("\n🔤 تست پردازش متن فارسی...")
    
    from bot import _prepare_text, infer_from_text
    
    test_texts = [
        "سلام دنیا",
        "متن بالا قرمز بزرگ",
        "Hello World",
        "سلام Hello ترکیبی"
    ]
    
    for text in test_texts:
        prepared = _prepare_text(text)
        inferred = infer_from_text(text)
        
        print(f"   متن: {text}")
        print(f"   آماده: {prepared}")
        print(f"   تشخیص: {inferred}")
        print()

async def main():
    print("=" * 60)
    print("🧪 تست API ربات استیکر فارسی")
    print("=" * 60)
    
    # تست توابع اصلی
    await test_bot_functions()
    
    # تست مدیریت کاربران
    test_user_management()
    
    # تست پردازش متن
    test_text_processing()
    
    print("=" * 60)
    print("✅ تست API کامل شد")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())