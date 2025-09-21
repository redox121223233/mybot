# handlers/messages.py
import logging
from config import BOT_TOKEN, CHANNEL_USERNAME, DATA_DIR
from utils.telegram_api import TelegramAPI
from services.sticker_manager import StickerManager
from services.ai_manager import AIManager

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)

# managers
sticker_manager = StickerManager(api, DATA_DIR)
ai_manager = AIManager(api, DATA_DIR)

# keyboard (reply keyboard)
MAIN_KB = {"keyboard": [["🎭 استیکرساز", "🤖 هوش مصنوعی"], ["⭐ اشتراک", "🎁 تست رایگان"]], "resize_keyboard": True}
BACK_KB = {"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}

def send_main_menu(chat_id):
    api.send_message(chat_id, "👋 خوش آمدی! یکی از گزینه‌ها را انتخاب کن:", reply_markup=MAIN_KB)

def handle_message(msg: dict):
    chat_id = msg["chat"]["id"]
    user_id = msg["from"]["id"]
    text = msg.get("text", "").strip() if msg.get("text") else None

    logger.info(f"📩 handle_message {user_id}: {text if text else '[non-text]'}")

    # membership check
    try:
        in_channel = api.is_user_in_channel(CHANNEL_USERNAME, user_id)
    except Exception as e:
        logger.error(f"❌ خطا در بررسی عضویت: {e}")
        in_channel = False

    if not in_channel:
        # send membership message with instruction
        channel_display = CHANNEL_USERNAME if not CHANNEL_USERNAME.startswith("@") else CHANNEL_USERNAME[1:]
        api.send_message(chat_id, f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n@{channel_display}\n\nسپس /start را بزنید ✅",
                         reply_markup={"keyboard":[[f"عضویت در @{channel_display}"],["/start"]], "resize_keyboard":True})
        return

    # /start
    if text == "/start":
        send_main_menu(chat_id)
        return

    # back
    if text == "⬅️ بازگشت":
        sticker_manager.cancel_flow(user_id)
        ai_manager.cancel_flow(user_id)
        send_main_menu(chat_id)
        return

    # menu choices
    if text == "🎭 استیکرساز":
        sticker_manager.start_flow(user_id)
        api.send_message(chat_id, "📦 لطفاً نام پک استیکر خود را وارد کنید:", reply_markup=BACK_KB)
        return

    if text == "🤖 هوش مصنوعی":
        ai_manager.start_flow(user_id)
        return

    if text == "⭐ اشتراک":
        api.send_message(chat_id, "⭐ بخش اشتراک (این بخش را می‌توان بعداً گسترش داد).", reply_markup=MAIN_KB)
        return

    if text == "🎁 تست رایگان":
        api.send_message(chat_id, "🎁 تست رایگان فعال شد (شبیه‌سازی).", reply_markup=MAIN_KB)
        return

    # اگر کاربر داخل فلو استیکر باشه
    if sticker_manager.is_in_flow(user_id):
        flow = sticker_manager.get_flow(user_id)
        step = flow.get("step")
        if step == "pack_name" and text:
            sticker_manager.set_pack_name(user_id, text)
            api.send_message(chat_id, "📷 نام پک ثبت شد. حالا عکس را ارسال کن:", reply_markup=BACK_KB)
            return
        if step == "text" and text is not None:
            # special /skip
            if text.strip() == "/skip":
                # create sticker without text
                sticker_manager.add_text_to_sticker(user_id, "")
            else:
                sticker_manager.add_text_to_sticker(user_id, text)
            return

    # اگر عکس ارسال شده
    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        # sticker flow expects photo
        if sticker_manager.is_in_flow(user_id) and sticker_manager.get_flow(user_id).get("step") == "photo":
            sticker_manager.process_sticker_photo(user_id, file_id)
            return
        # ai flow
        if ai_manager.is_in_flow(user_id):
            ai_manager.process_ai_photo(user_id, file_id)
            return

    # fallback
    api.send_message(chat_id, "متوجه نشدم. از منوی اصلی استفاده کن.", reply_markup=MAIN_KB)
