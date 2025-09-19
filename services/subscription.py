from utils.keyboards import send_message

def activate_trial(chat_id):
    send_message(chat_id, "🎁 دوره رایگان ۳ روزه فعال شد ✅")

def show_plans(chat_id, message_id=None):
    send_message(chat_id, "⭐ پلن‌های اشتراک:\n1 ماهه - 10T\n3 ماهه - 25T")
