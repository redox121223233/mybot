class MenuManager:
    def __init__(self, api, bot_token):
        self.api = api
        self.bot_token = bot_token

    def main_menu(self):
        """منوی اصلی ربات"""
        return {
            "keyboard": [
                [{"text": "🎭 استیکرساز"}],
                [{"text": "⭐ اشتراک"}],
                [{"text": "🎁 تست رایگان"}],
                [{"text": "🤖 هوش مصنوعی"}],
            ],
            "resize_keyboard": True
        }

    def back_button(self):
        """دکمه بازگشت به منوی اصلی"""
        return {
            "keyboard": [
                [{"text": "⬅️ بازگشت"}]
            ],
            "resize_keyboard": True
        }

    def show_main_menu(self, user_id):
        """ارسال منوی اصلی به کاربر"""
        self.api.send_message(user_id, "منوی اصلی 👇", reply_markup=self.main_menu())
