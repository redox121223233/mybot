import logging
from config import CHANNEL_USERNAME
from utils.telegram_api import TelegramAPI
from services.sticker_manager import StickerManager

logger = logging.getLogger(__name__)
api = TelegramAPI("توکن_ربات")  # ← اینو با توکن واقعی‌ات ست کن
sticker_manager = StickerManager(api)

# وضعیت کاربران
user_flows = {}

def handle_message(message):
    user_id = message["from"]["id"]
    text = message.get("text", "")

    logger.info(f"📩 handle_message {user_id}: {text}")

    # بررسی عضویت اجباری
    try:
        if not api.is_user_in_channel(CHANNEL_USERNAME, user_id):
            api.send_message(
                user_id,
                f"📢 برای استفاده از ربات ابتدا در کانال عضو شوید:\n{CHANNEL_USERNAME}\n\nسپس /start را بزنید ✅"
            )
            return
    except Exception as e:
        logger.error(f"❌ خطا در بررسی عضویت: {e}")
        return

    # شروع
    if text == "/start":
        user_flows[user_id] = {"step": "menu"}
        show_main_menu(user_id)
        return

    # اگر در جریان استیکرسازی است
    if user_id in user_flows:
        flow = user_flows[user_id]
        step = flow.get("step")

        # منوی اصلی
        if step == "menu":
            if text == "🎭 استیکرساز":
                flow["step"] = "sticker_photo"
                api.send_message(user_id, "📷 لطفاً عکس خود را بفرستید:",
                                 reply_markup={"keyboard":[["⬅️ بازگشت"]], "resize_keyboard": True})
                return

            elif text == "🤖 هوش مصنوعی":
                flow["step"] = "ai_chat"
                api.send_message(user_id, "💬 پیام خود را بفرستید:",
                                 reply_markup={"keyboard":[["⬅️ بازگشت"]], "resize_keyboard": True})
                return

        # مرحله استیکرساز
        if step == "sticker_photo":
            if text == "⬅️ بازگشت":
                show_main_menu(user_id)
                return
            if "photo" in message:
                flow["photo_id"] = message["photo"][-1]["file_id"]
                flow["step"] = "sticker_text"
                api.send_message(user_id, "✍️ متن موردنظر را وارد کنید:")
                return
            api.send_message(user_id, "❌ لطفاً یک عکس بفرستید یا بازگشت بزنید.")
            return

        if step == "sticker_text":
            if text == "⬅️ بازگشت":
                flow["step"] = "sticker_photo"
                api.send_message(user_id, "📷 دوباره عکس خود را بفرستید:")
                return
            flow["sticker_text"] = text
            flow["step"] = "sticker_font"
            api.send_message(user_id, "🎨 فونت خود را انتخاب کنید:",
                             reply_markup={"keyboard":[["ساده", "بولد"],["نستعلیق"],["⬅️ بازگشت"]], "resize_keyboard": True})
            return

        if step == "sticker_font":
            if text == "⬅️ بازگشت":
                flow["step"] = "sticker_text"
                api.send_message(user_id, "✍️ متن خود را دوباره وارد کنید:")
                return
            flow["font"] = text
            flow["step"] = "sticker_color"
            api.send_message(user_id, "🎨 رنگ متن را انتخاب کنید:",
                             reply_markup={"keyboard":[["⚪️ سفید","🔴 قرمز"],["🔵 آبی","🟢 سبز"],["⬅️ بازگشت"]], "resize_keyboard": True})
            return

        if step == "sticker_color":
            if text == "⬅️ بازگشت":
                flow["step"] = "sticker_font"
                api.send_message(user_id, "🎨 دوباره فونت خود را انتخاب کنید:")
                return
            flow["color"] = text
            flow["step"] = "sticker_position"
            api.send_message(user_id, "📍 موقعیت متن را انتخاب کنید:",
                             reply_markup={"keyboard":[["⬆️ بالا","⬇️ پایین"],["➡️ وسط"],["⬅️ بازگشت"]], "resize_keyboard": True})
            return

        if step == "sticker_position":
            if text == "⬅️ بازگشت":
                flow["step"] = "sticker_color"
                api.send_message(user_id, "🎨 دوباره رنگ متن را انتخاب کنید:")
                return
            flow["position"] = text
            flow["step"] = "sticker_done"
            api.send_message(user_id, "✅ استیکر شما در حال ساخته شدن است...")

            # ساخت استیکر
            sticker_manager.build_sticker(user_id, flow)
            show_main_menu(user_id)
            return

        # بخش هوش مصنوعی
        if step == "ai_chat":
            if text == "⬅️ بازگشت":
                show_main_menu(user_id)
                return
            # 🔥 اینجا بعدا میشه GPT واقعی وصل کرد
            api.send_message(user_id, f"🤖 پاسخ هوش مصنوعی:\n\n{text[::-1]}")
            return

    api.send_message(user_id, "❌ متوجه نشدم. از منو استفاده کنید.")


def show_main_menu(user_id):
    user_flows[user_id] = {"step": "menu"}
    api.send_message(
        user_id,
        "👋 به ربات خوش آمدید!\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup={
            "keyboard":[
                ["🎭 استیکرساز"],
                ["🤖 هوش مصنوعی"]
            ],
            "resize_keyboard": True
        }
    )
