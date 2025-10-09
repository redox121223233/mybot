#!/usr/bin/env python3
"""
تست محیط سرورلس برای بررسی Event Loop Closed
"""
import asyncio
import json
from api.bot_functions import process_update

# تست داده callback_query
test_callback_data = {
    'update_id': 10731363,
    'callback_query': {
        'id': '7553183702577587009',
        'from': {
            'id': 6053579919,
            'is_bot': False,
            'first_name': 'ᖇᗴᗞᝪ᙭',
            'username': 'onedaytoalive',
            'language_code': 'fa'
        },
        'message': {
            'message_id': 23144,
            'from': {
                'id': 8324626018,
                'is_bot': True,
                'first_name': 'استیکرساز REDOX',
                'username': 'matnsticker_bot'
            },
            'chat': {
                'id': 6053579919,
                'first_name': 'ᖇᗴᗞᝪ᙭',
                'username': 'onedaytoalive',
                'type': 'private'
            },
            'date': 1760032203,
            'text': 'سلام! خوش اومدی ✨\nیکی از گزینه\u200cهای زیر رو انتخاب کن:',
            'reply_markup': {
                'inline_keyboard': [[
                    {'text': 'استیکر ساده 🪄', 'callback_data': 'menu:simple'},
                    {'text': 'استیکر هوش مصنوعی 🤖', 'callback_data': 'menu:ai'}
                ]]
            }
        },
        'chat_instance': '2334786973202696998',
        'data': 'menu:simple'
    }
}

def test_serverless_processing():
    """تست پردازش در محیط سرورلس با مدیریت event loop"""
    print("🧪 تست محیط سرورلس...")
    
    try:
        # شبیه‌سازی محیط سرورلس - ایجاد event loop جدید برای هر درخواست
        import asyncio
        
        # ایجاد event loop جدید (مثل سرورلس)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # پردازش update
            loop.run_until_complete(process_update(test_callback_data))
            print("✅ Serverless processing successful!")
            
            # بستن event loop (مثل سرورلس)
            loop.close()
            
            # تست دوم - شبیه‌سازی درخواست بعدی
            print("🔄 تست درخواست دوم (شبیه‌سازی درخواست جدید)...")
            
            loop2 = asyncio.new_event_loop()
            asyncio.set_event_loop(loop2)
            
            try:
                loop2.run_until_complete(process_update(test_callback_data))
                print("✅ Second request processed successfully!")
            finally:
                loop2.close()
                
            print("✅ Event Loop Closed problem is fixed!")
            return True
            
        except Exception as e:
            print(f"❌ Error in serverless simulation: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Error setting up event loop: {e}")
        return False

if __name__ == "__main__":
    result = test_serverless_processing()
    if result:
        print("\n🎉 مشکل Event Loop Closed حل شده!")
        print("🎉 ربات حالا در محیط سرورلس بدون مشکل کار می‌کنه!")
    else:
        print("\n⚠️ هنوز مشکلی وجود دارد.")