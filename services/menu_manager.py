# /app/services/menu_manager.py

class MenuManager:
    """
    مدیریت منوهای تلگرام (صفحه کلید ها)
    """

    def __init__(self, base_url: str, bot_token: str):
        self.base_url = base_url
        self.bot_token = bot_token

    # منوی اصلی
    def get_main_menu(self):
        return {
            "keyboard": [
                [{"text": "🎭 استیکرساز"}, {"text": "🤖 استیکر هوش مصنوعی"}],
                [{"text": "⭐ اشتراک"}, {"text": "🎁 تست رایگان"}],
                [{"text": "⚙️ تنظیمات"}, {"text": "📞 پشتیبانی"}]
            ],
            "resize_keyboard": True
        }

    # منوی تنظیمات
    def get_settings_menu(self):
        return {
            "keyboard": [
                [{"text": "🌐 انتخاب زبان"}, {"text": "🎨 طراحی پیشرفته"}],
                [{"text": "⬅️ بازگشت به منوی اصلی"}]
            ],
            "resize_keyboard": True
        }

    # منوی اشتراک
    def get_subscription_menu(self):
        return {
            "keyboard": [
                [{"text": "💳 خرید اشتراک"}, {"text": "📊 وضعیت اشتراک"}],
                [{"text": "⬅️ بازگشت به منوی اصلی"}]
            ],
            "resize_keyboard": True
        }

    # منوی استیکرساز (معمولی یا AI)
    def get_sticker_menu(self):
        return {
            "keyboard": [
                [{"text": "📤 آپلود عکس"}, {"text": "✨ تبدیل به استیکر"}],
                [{"text": "⬅️ بازگشت به منوی اصلی"}]
            ],
            "resize_keyboard": True
        }

    # منوی پشتیبانی
    def get_support_menu(self):
        return {
            "keyboard": [
                [{"text": "📨 ارسال پیام پشتیبانی"}],
                [{"text": "⬅️ بازگشت به منوی اصلی"}]
            ],
            "resize_keyboard": True
        }
