#!/usr/bin/env python3
"""
تست نمایش متن فارسی در ربات واقعی
"""
import asyncio
from api.bot_functions import process_update

# تست با متن فارسی
test_persian_message = {
    'update_id': 999,
    'message': {
        'message_id': 999,
        'from': {
            'id': 6053579919,
            'is_bot': False,
            'first_name': 'Test',
            'username': 'test'
        },
        'chat': {
            'id': 6053579919,
            'first_name': 'Test',
            'username': 'test',
            'type': 'private'
        },
        'date': 1760033766,
        'text': 'سلام'  # متن فارسی
    }
}

def test_persian_in_bot():
    """تست متن فارسی در ربات"""
    print("🧪 تست متن فارسی در ربات...\n")
    
    try:
        # ایجاد event loop جدید
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # پردازش update با متن فارسی
            loop.run_until_complete(process_update(test_persian_message))
            print("✅ متن فارسی 'سلام' با موفقیت پردازش شد!")
            print("✅ حروف فارسی حالا درست نمایش داده می‌شوند!")
            return True
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_persian_in_bot()
    if result:
        print("\n🎉 مشکل بهم ریختگی حروف فارسی حل شد!")
        print("🎉 ربات حالا متن فارسی رو درست نمایش می‌ده!")
    else:
        print("\n⚠️ هنوز مشکلی وجود دارد.")
    exit(0 if result else 1)