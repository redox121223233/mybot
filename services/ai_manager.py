# services/ai_manager.py
import logging

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self, api):
        self.api = api
        self.user_states = {}  # ذخیره وضعیت کاربرها

    def start_ai_flow(self, user_id: int):
        """شروع فرآیند طراحی با هوش مصنوعی (شبه‌سازی ساده)"""
        self.user_states[user_id] = "waiting_for_photo"
        self.api.send_message(user_id, "📸 لطفاً عکس خود را ارسال کنید تا طراحی آغاز شود.")

    def is_in_ai_flow(self, user_id: int) -> bool:
        """بررسی اینکه آیا کاربر در فرآیند هوش مصنوعی هست یا نه"""
        return user_id in self.user_states

    def process_ai_photo(self, user_id: int, file_id: str):
        """دریافت عکس و ادامه‌ی فرآیند"""
        if self.user_states.get(user_id) == "waiting_for_photo":
            # در آینده اینجا میشه متن/افکت/موقعیت اضافه کرد
            self.api.send_message(user_id, "✅ عکس دریافت شد! حالا متنی که میخوای روی عکس باشه رو بفرست.")
            self.user_states[user_id] = "waiting_for_text"
        else:
            self.api.send_message(user_id, "لطفاً دوباره از منوی هوش مصنوعی شروع کنید.")

    def process_ai_text(self, user_id: int, text: str):
        """دریافت متن و نهایی کردن طراحی"""
        if self.user_states.get(user_id) == "waiting_for_text":
            # اینجا فعلاً شبیه‌سازی میکنیم
            self.api.send_message(user_id, f"🖼 طراحی شما با متن: «{text}» ساخته شد! (نسخه نمایشی)")
            del self.user_states[user_id]
        else:
            self.api.send_message(user_id, "❌ شما در حالت طراحی نیستید. از منوی هوش مصنوعی شروع کنید.")
