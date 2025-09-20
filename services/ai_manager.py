
import logging

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self, api):
        self.api = api
        self.user_flows = {}

    def start_ai_flow(self, user_id):
        self.user_flows[user_id] = {"step": "waiting_input"}
        self.api.send_message(
            user_id,
            "✍️ متن یا دستور طراحی خود را وارد کنید:",
            reply_markup={"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}
        )

    def is_in_ai_flow(self, user_id):
        return user_id in self.user_flows

    def cancel_flow(self, user_id):
        """لغو فلو هوش مصنوعی"""
        if user_id in self.user_flows:
            del self.user_flows[user_id]
            logger.info(f"↩️ AI flow canceled for {user_id}")

    def process_ai_text(self, user_id, text):
        if not self.is_in_ai_flow(user_id):
            return
        # اینجا بعداً می‌تونیم پردازش هوش مصنوعی واقعی بذاریم
        self.api.send_message(user_id, f"🤖 جواب هوش مصنوعی برای: {text}")
        self.cancel_flow(user_id)

    def process_ai_photo(self, user_id, file_id):
        if not self.is_in_ai_flow(user_id):
            return
        # فعلاً فقط اطلاع بده
        self.api.send_message(user_id, "📷 عکس دریافت شد! (فعلاً پردازشی انجام نمی‌دهیم)")
        self.cancel_flow(user_id)
