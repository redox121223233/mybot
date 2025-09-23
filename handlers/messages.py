from services import sticker_manager
from utils.state_manager import get_state, set_state

def handle_message(api, update):
    message = update.get("message", {})
    chat_id = message["chat"]["id"]
    text = message.get("text")
    photo = message.get("photo")

    if text == "/start":
        api.send_message(
            chat_id,
            "👋 خوش آمدید!\nیکی از گزینه‌ها رو انتخاب کنید:",
            reply_markup={
                "keyboard": [
                    [{"text": "🎭 استیکرساز"}],
                    [{"text": "🤖 هوش مصنوعی"}],
                    [{"text": "⚙️ تنظیمات"}],
                ],
                "resize_keyboard": True,
            },
        )
        return

    # استیکرساز
    if text == "🎭 استیکرساز":
        api.send_message(chat_id, "📸 لطفاً یک عکس ارسال کنید تا به استیکر تبدیل بشه.")
        set_state(chat_id, "awaiting_photo")
        return

    if photo and get_state(chat_id) == "awaiting_photo":
        file_id = photo[-1]["file_id"]
        sticker_manager.handle_sticker_upload(api, chat_id, file_id)
        return

    if text in ["بله ✍️", "خیر 🚫"]:
        sticker_manager.handle_text_choice(api, chat_id, text)
        return

    if get_state(chat_id) == "awaiting_text":
        sticker_manager.handle_text_input(api, chat_id, text)
        return
