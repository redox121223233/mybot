
from utils.telegram_api import TelegramAPI

class MenuManager:
    def __init__(self, api: TelegramAPI, bot_token: str):
        self.api = api
        self.bot_token = bot_token

    def main_keyboard_markup(self):
        kb = {
            "keyboard": [
                [{"text": "🎭 استیکرساز"}, {"text": "🤖 استیکر هوش مصنوعی"}],
                [{"text": "⭐ اشتراک"}, {"text": "🎁 تست رایگان"}],
                [{"text": "⚙️ تنظیمات"}]
            ],
            "resize_keyboard": True
        }
        return kb

    def subscription_inline_markup(self):
        return {
            "inline_keyboard": [
                [{"text": "💳 خرید اشتراک", "callback_data": "buy_sub"}],
                [{"text": "📊 وضعیت اشتراک", "callback_data": "check_sub"}]
            ]
        }
