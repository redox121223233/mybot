# handlers/messages.py
import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN
from services.sticker_manager import handle_sticker_upload
from services.ai_manager import generate_sticker
from services.setting_manager import get_user_settings

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# وضعیت کاربرها (مثلاً انتخاب استیکرساز، هوش مصنوعی و ...)
user_states = {}

def handle_message(update):
    try:
        message = update.get("message", {})
        user_id = message.get("from", {}).get("id")
        text = message.get("text")
        photos = message.get("photo")

        logger.info(f"📩 handle_message {user_id}: {text if text else '[photo]'}")

        if not user_id:
            return

        # اگر کاربر /start زد
        if text == "/start":
            api.send_message(
                user_id,
                "👋 خوش آمدید!\nیکی از گزینه‌ها رو انتخاب کنید:",
                reply_markup={
                    "keyboard": [[{"text": "🎭 استیکرساز"}],
                                 [{"text": "🤖 هوش مصنوعی"}],
                                 [{"text": "⚙️ تنظیمات"}]],
                    "resize_keyboard": True
                }
            )
            user_states[user_id] = None
            return

        # استیکرساز
        if text == "🎭 استیکرساز":
            api.send_message(user_id, "📸 لطفاً یک عکس ارسال کنید تا به استیکر تبدیل بشه.")
            user_states[user_id] = "sticker"
            return

        # هوش مصنوعی
        if text == "🤖 هوش مصنوعی":
            api.send_message(user_id, "📝 متن خودت رو بفرست تا تبدیل به استیکر بشه.")
            user_states[user_id] = "ai"
            return

        # تنظیمات
        if text == "⚙️ تنظیمات":
            settings = get_user_settings(user_id)
            api.send_message(user_id, f"⚙️ تنظیمات فعلی شما:\n{settings}")
            return

        # اگر کاربر عکس فرستاد و تو حالت استیکرسازه
        if photos and user_states.get(user_id) == "sticker":
            handle_sticker_upload(update, user_id, pack_name="test_pack")
            return

        # اگر کاربر متن فرستاد و تو حالت هوش مصنوعیه
        if text and user_states.get(user_id) == "ai":
            result = generate_sticker(text, user_id)
            api.send_message(user_id, result)
            return

    except Exception as e:
        logger.error(f"❌ Error handling update: {e}", exc_info=True)
