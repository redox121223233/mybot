import logging
from config import CHANNEL_USERNAME
from services.sticker_manager import handle_sticker_upload
from services.ai_manager import generate_sticker
from services.setting_manager import get_user_settings

logger = logging.getLogger(__name__)

# ------------------ هندل پیام ------------------
def handle_message(update, api):
    try:
        message = update.get("message", {})
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]

        text = message.get("text")
        photo = message.get("photo")

        logger.info(f"📩 handle_message {user_id}: {text or '[photo]'}")

        # 1️⃣ بررسی عضویت
        if not api.is_user_in_channel(CHANNEL_USERNAME, user_id):
            api.send_message(
                chat_id,
                f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n{CHANNEL_USERNAME}\n\nسپس /start را بزنید ✅"
            )
            return

        # 2️⃣ هندل /start
        if text == "/start":
            send_main_menu(api, chat_id)
            return

        # 3️⃣ استیکرساز
        if text == "🎭 استیکرساز":
            api.send_message(chat_id, "📸 لطفاً یک تصویر ارسال کنید تا تبدیل به استیکر شود.")
            return

        if photo:
            file_id = photo[-1]["file_id"]  # بزرگ‌ترین سایز
            handle_sticker_upload(api, chat_id, user_id, file_id)
            return

        # 4️⃣ هوش مصنوعی
        if text == "🤖 هوش مصنوعی":
            api.send_message(chat_id, "📝 متن خود را بفرستید تا تبدیل به استیکر هوشمند شود.")
            return

        # اگر متن معمولی است → استیکر با AI
        if text:
            sticker = generate_sticker(text, user_id)
            api.send_message(chat_id, sticker)
            return

        # 5️⃣ fallback
        api.send_message(chat_id, "🤔 متوجه نشدم. از منو یکی از گزینه‌ها را انتخاب کنید.")

    except Exception as e:
        logger.error(f"❌ Error handling update: {e}")


# ------------------ ارسال منوی اصلی ------------------
def send_main_menu(api, chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "🎭 استیکرساز"}],
            [{"text": "🤖 هوش مصنوعی"}],
            [{"text": "⚙️ تنظیمات"}, {"text": "🔄 ریست تنظیمات"}],
        ],
        "resize_keyboard": True
    }
    api.send_message(chat_id, "👋 خوش آمدید! یکی از گزینه‌های زیر را انتخاب کنید:", reply_markup=keyboard)
