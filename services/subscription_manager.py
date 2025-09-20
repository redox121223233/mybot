# services/subscription_manager.py
import logging

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, db_manager, filename):
        self.db_manager = db_manager
        self.filename = filename
        self.user_states = {}

    def show_subscription_menu(self, user_id):
        """نمایش منوی اشتراک به کاربر"""
        from services.legacy import api, menu_manager  # جلوگیری از import loop

        text = "📌 منوی اشتراک:\n\n" \
               "1️⃣ خرید اشتراک\n" \
               "2️⃣ مشاهده وضعیت اشتراک\n" \
               "3️⃣ لغو"

        keyboard = [
            [{"text": "🔑 خرید اشتراک"}],
            [{"text": "📊 وضعیت من"}],
            [{"text": "⬅️ بازگشت"}]
        ]

        logger.info(f"نمایش منوی اشتراک به کاربر {user_id}")
        api.send_message(user_id, text, reply_markup={"keyboard": keyboard, "resize_keyboard": True})

    def handle_subscription_action(self, user_id, text):
        """مدیریت انتخاب‌های کاربر در بخش اشتراک"""
        from services.legacy import api, menu_manager

        if text == "🔑 خرید اشتراک":
            api.send_message(user_id, "💳 لینک خرید اشتراک: example.com/buy")
        elif text == "📊 وضعیت من":
            api.send_message(user_id, "⌛ شما هیچ اشتراک فعالی ندارید.")
        elif text == "⬅️ بازگشت":
            menu_manager.show_main_menu(user_id)
        else:
            api.send_message(user_id, "❌ گزینه اشتباه. از منوی اشتراک انتخاب کنید.")
