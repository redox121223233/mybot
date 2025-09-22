# services/menu_manager.py
import json

# ------------------ منوی اصلی ------------------
def get_main_menu():
    return json.dumps({
        "keyboard": [
            [{"text": "🎭 استیکرساز"}],
            [{"text": "🤖 هوش مصنوعی"}],
            [{"text": "⚙️ تنظیمات"}, {"text": "🔄 بازنشانی"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    })

# ------------------ منوی تنظیمات ------------------
def get_settings_menu():
    return json.dumps({
        "keyboard": [
            [{"text": "🎨 تغییر رنگ متن"}, {"text": "🔤 تغییر فونت"}],
            [{"text": "📍 تغییر موقعیت"}, {"text": "⬅️ بازگشت"}]
        ],
        "resize_keyboard": True
    })
