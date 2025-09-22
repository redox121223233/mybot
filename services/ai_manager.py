import logging
from utils.telegram_api import TelegramAPI
from config import BOT_TOKEN

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# وضعیت کاربران
ai_states = {}

def start_ai_flow(user_id, chat_id):
    ai_states[user_id] = {"step": "await_text"}
    api.send_message(chat_id, "🤖 متن یا ایده‌ات رو بفرست تا استیکر هوش مصنوعی بسازیم:")

def handle_ai_message(message):
    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    text = message.get("text")

    state = ai_states.get(user_id, {})

    # مرحله گرفتن متن
    if state.get("step") == "await_text" and text:
        state["prompt"] = text.strip()
        state["step"] = "confirm"
        api.send_message(
            chat_id,
            f"🔍 متن دریافتی:\n\n{text}\n\nآیا همین متن برای ساخت استیکر استفاده شود؟ (بزن بله یا نه)"
        )
        return

    # مرحله تأیید
    if state.get("step") == "confirm" and text:
        if text.strip() in ["بله", "Yes", "yes", "اره"]:
            build_ai_sticker(user_id, chat_id)
        else:
            state["step"] = "await_text"
            api.send_message(chat_id, "✍️ متن جدیدت رو بفرست:")
        return

    api.send_message(chat_id, "❌ متوجه نشدم! از گزینه‌ها استفاده کن.")

def build_ai_sticker(user_id, chat_id):
    state = ai_states.get(user_id, {})
    prompt = state.get("prompt")

    if not prompt:
        api.send_message(chat_id, "⚠️ متنی پیدا نشد! دوباره شروع کن.")
        return

    try:
        # اینجا میشه هوش مصنوعی تصویرساز مثل DALL·E یا StableDiffusion وصل کرد
        fake_result = f"[استیکر ساخته‌شده از متن: {prompt}]"
        api.send_message(chat_id, f"✅ استیکر ساخته شد:\n{fake_result}")
    except Exception as e:
        logger.error(f"❌ خطا در ساخت استیکر AI: {e}")
        api.send_message(chat_id, "❌ خطا در ساخت استیکر هوش مصنوعی.")

    ai_states.pop(user_id, None)

def send_ai_help(chat_id):
    help_text = (
        "📘 راهنمای هوش مصنوعی:\n\n"
        "1️⃣ متن یا ایده‌ای بفرست (مثل: «یک ربات در فضا»).\n"
        "2️⃣ ربات ازت تأیید می‌گیره.\n"
        "3️⃣ با بله، استیکر ساخته میشه.\n"
        "4️⃣ با نه، می‌تونی متن جدید بدی.\n\n"
        "⚙️ آینده: امکان انتخاب رنگ، فونت و موقعیت متن."
    )
    api.send_message(chat_id, help_text)
