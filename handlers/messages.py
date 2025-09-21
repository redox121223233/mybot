import logging
from config import CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI

api = TelegramAPI()

# 📌 تابع ارسال منوی اصلی
def send_main_menu(chat_id):
    api.send_message(
        chat_id,
        "👋 خوش اومدی به استیکرساز REDOX!\n\nاز دکمه‌های زیر استفاده کن:",
        reply_markup={
            "keyboard": [
                ["🎭 استیکرساز", "🤖 هوش مصنوعی"],
                ["ℹ️ راهنما", "❌ خروج"]
            ],
            "resize_keyboard": True
        }
    )

def handle_message(message):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    logging.info(f"📩 handle_message {user_id}: {text}")

    # اول چک عضویت
    try:
        if not api.is_user_in_channel(user_id, CHANNEL_USERNAME):
            api.send_message(
                chat_id,
                f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n👉 {CHANNEL_USERNAME}\n\nبعد از عضویت، روی دکمه زیر بزنید:",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "✅ عضو شدم - شروع", "callback_data": "restart_bot"}]
                    ]
                }
            )
            return
    except Exception as e:
        logging.error(f"❌ خطا در بررسی عضویت: {e}")
        return

    # دستورات ربات
    if text == "/start":
        send_main_menu(chat_id)

    elif text == "🎭 استیکرساز":
        api.send_message(chat_id, "📸 لطفاً عکس مورد نظرت رو بفرست تا استیکر بسازم.")

    elif text == "🤖 هوش مصنوعی":
        api.send_message(chat_id, "🧠 پیام یا سوالت رو بفرست تا با هوش مصنوعی جواب بدم.")

    elif text == "ℹ️ راهنما":
        api.send_message(chat_id, "📖 راهنما:\n\n- 🎭 استیکرساز → عکس بده، متن بده، استیکر تحویل بگیر.\n- 🤖 هوش مصنوعی → هرچی بپرسی جواب میده.\n- ❌ خروج → پایان گفتگو.")

    elif text == "❌ خروج":
        api.send_message(chat_id, "👋 خداحافظ! هر وقت خواستی دوباره برگرد /start رو بزن.")

    else:
        api.send_message(chat_id, "❓ متوجه نشدم! از منوی اصلی استفاده کن.")
