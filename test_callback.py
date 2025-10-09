#!/usr/bin/env python3
"""
تست callback_query برای بررسی اینکه آیا دکمه‌های اینلاین کار می‌کنند
"""
import asyncio
import json
from api.bot_functions import process_update

# یک نمونه callback_query شبیه لاگی که فرستادی
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
                ], [
                    {'text': 'سهمیه امروز ⏳', 'callback_data': 'menu:quota'},
                    {'text': 'راهنما ℹ️', 'callback_data': 'menu:help'}
                ], [
                    {'text': 'اشتراک / نظرسنجی 📊', 'callback_data': 'menu:sub'},
                    {'text': 'پشتیبانی 🛟', 'callback_data': 'menu:support'}
                ], [
                    {'text': 'پنل ادمین 🛠', 'callback_data': 'menu:admin'}
                ]]
            }
        },
        'chat_instance': '2334786973202696998',
        'data': 'menu:simple'
    }
}

async def test_callback():
    """تست پردازش callback_query"""
    print("🧪 در حال تست callback_query...")
    try:
        await process_update(test_callback_data)
        print("✅ Callback query processed successfully!")
        print("✅ Router attachment error is fixed!")
        return True
    except Exception as e:
        print(f"❌ Error processing callback query: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_callback())
    if result:
        print("\n🎉 مشکل Router Attachment حل شده!")
        print("🎉 دکمه‌های اینلاین باید کار کنند!")
    else:
        print("\n⚠️ هنوز مشکلی وجود دارد.")