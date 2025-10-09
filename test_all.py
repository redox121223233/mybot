#!/usr/bin/env python3
"""
تست کامل تمام سناریوهای ربات
"""
import asyncio
from api.bot_functions import process_update

# تست داده‌های مختلف
test_cases = [
    {
        'name': '/start command',
        'data': {
            'update_id': 1,
            'message': {
                'message_id': 1,
                'from': {'id': 6053579919, 'is_bot': False, 'first_name': 'Test', 'username': 'test'},
                'chat': {'id': 6053579919, 'first_name': 'Test', 'username': 'test', 'type': 'private'},
                'date': 1760033766,
                'text': '/start',
                'entities': [{'offset': 0, 'length': 6, 'type': 'bot_command'}]
            }
        }
    },
    {
        'name': 'Inline button callback',
        'data': {
            'update_id': 2,
            'callback_query': {
                'id': '123',
                'from': {'id': 6053579919, 'is_bot': False, 'first_name': 'Test', 'username': 'test'},
                'message': {
                    'message_id': 2,
                    'from': {'id': 8324626018, 'is_bot': True, 'first_name': 'Bot', 'username': 'bot'},
                    'chat': {'id': 6053579919, 'first_name': 'Test', 'username': 'test', 'type': 'private'},
                    'date': 1760033766,
                    'text': 'Test message'
                },
                'chat_instance': '123',
                'data': 'menu:simple'
            }
        }
    },
    {
        'name': 'Text message',
        'data': {
            'update_id': 3,
            'message': {
                'message_id': 3,
                'from': {'id': 6053579919, 'is_bot': False, 'first_name': 'Test', 'username': 'test'},
                'chat': {'id': 6053579919, 'first_name': 'Test', 'username': 'test', 'type': 'private'},
                'date': 1760033766,
                'text': 'سلام'
            }
        }
    }
]

def test_all_scenarios():
    """تست تمام سناریوها"""
    print("🧪 شروع تست کامل ربات...\n")
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"📝 تست {i}/{len(test_cases)}: {test_case['name']}")
        
        try:
            # ایجاد event loop جدید برای هر تست (شبیه‌سازی سرورلس)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # پردازش update
                loop.run_until_complete(process_update(test_case['data']))
                print(f"   ✅ موفق\n")
                passed += 1
            finally:
                loop.close()
                
        except Exception as e:
            print(f"   ❌ خطا: {e}\n")
            failed += 1
    
    # نتیجه نهایی
    print("=" * 50)
    print(f"📊 نتایج تست:")
    print(f"   ✅ موفق: {passed}/{len(test_cases)}")
    print(f"   ❌ ناموفق: {failed}/{len(test_cases)}")
    print("=" * 50)
    
    if failed == 0:
        print("\n🎉 تمام تست‌ها موفق بودند!")
        print("🎉 ربات آماده استفاده در Vercel است!")
        return True
    else:
        print(f"\n⚠️ {failed} تست ناموفق بود.")
        return False

if __name__ == "__main__":
    result = test_all_scenarios()
    exit(0 if result else 1)