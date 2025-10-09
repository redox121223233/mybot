#!/usr/bin/env python3
"""
تست دستور /start برای بررسی کامل عملکرد ربات
"""
import asyncio
from api.bot_functions import process_update

# تست داده /start command
test_start_data = {
    'update_id': 10731377,
    'message': {
        'message_id': 23157,
        'from': {
            'id': 6053579919,
            'is_bot': False,
            'first_name': 'ᖇᗴᗞᝪ᙭',
            'username': 'onedaytoalive',
            'language_code': 'fa'
        },
        'chat': {
            'id': 6053579919,
            'first_name': 'ᖇᗴᗞᝪ᙭',
            'username': 'onedaytoalive',
            'type': 'private'
        },
        'date': 1760033766,
        'text': '/start',
        'entities': [{'offset': 0, 'length': 6, 'type': 'bot_command'}]
    }
}

def test_start_command():
    """تست دستور /start در محیط سرورلس"""
    print("🧪 تست دستور /start...")
    
    try:
        # شبیه‌سازی محیط سرورلس
        import asyncio
        
        # ایجاد event loop جدید
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # پردازش update
            loop.run_until_complete(process_update(test_start_data))
            print("✅ /start command processed successfully!")
            
            # بستن event loop
            loop.close()
            
            print("✅ No errors occurred!")
            return True
            
        except Exception as e:
            print(f"❌ Error processing /start: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Error setting up test: {e}")
        return False

if __name__ == "__main__":
    result = test_start_command()
    if result:
        print("\n🎉 دستور /start بدون مشکل کار می‌کنه!")
        print("🎉 ربات آماده استفاده در Vercel است!")
    else:
        print("\n⚠️ هنوز مشکلی وجود دارد.")