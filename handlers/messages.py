from utils.keyboards import main_menu, send_message
from services import database, subscription

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = msg.get("text")

    if text == "/start":
        database.add_user(chat_id)
        main_menu(chat_id)

    elif text == "🎁 تست رایگان":
        subscription.activate_trial(chat_id)

    elif text == "⭐ اشتراک":
        subscription.show_plans(chat_id)

    elif text == "🎭 استیکرساز":
        database.set_mode(chat_id, "sticker")
        send_message(chat_id, "🎭 استیکرساز فعال شد. عکس یا استیکر بفرست.")
