from services import subscription, ai
from utils.keyboards import send_message

def handle_callback(cb):
    data = cb["data"]
    chat_id = cb["message"]["chat"]["id"]
    message_id = cb["message"]["message_id"]

    if data == "ai_activate":
        ai.toggle(chat_id, True)
        send_message(chat_id, "هوش مصنوعی فعال شد ✅")

    elif data == "change_lang":
        send_message(chat_id, "🌐 انتخاب زبان:\n🇮🇷 فارسی | 🇬🇧 English")

    elif data == "show_subscription":
        subscription.show_plans(chat_id, message_id)
