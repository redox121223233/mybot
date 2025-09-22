import os
import logging
from utils.telegram_api import TelegramAPI
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

api = TelegramAPI(token=os.getenv("BOT_TOKEN"))
DATA_DIR = "/tmp"

# حافظه ساده برای مرحله‌ها
user_sessions = {}


def resize_to_sticker_size(input_path, output_path, text=None):
    """تغییر اندازه به 512x512 + نوشتن متن (اختیاری)"""
    with Image.open(input_path) as img:
        img = img.convert("RGBA")
        img = img.resize((512, 512), Image.LANCZOS)

        if text:
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 36)
            except:
                font = ImageFont.load_default()

            text_w, text_h = draw.textsize(text, font=font)
            x = (img.width - text_w) // 2
            y = img.height - text_h - 10
            draw.text((x, y), text, font=font, fill="white")

        img.save(output_path, format="PNG")


def handle_sticker_upload(update, user_id, pack_name):
    """دریافت عکس → سوال متن یا نه"""
    try:
        message = update.get("message", {})
        photos = message.get("photo")
        if not photos:
            return False

        file_id = photos[-1]["file_id"]
        dest_path = os.path.join(DATA_DIR, f"{user_id}_sticker.png")
        api.download_file(file_id, dest_path)

        # ذخیره مسیر برای این کاربر
        user_sessions[user_id] = {"image": dest_path, "pack": pack_name}

        # سوال بعدی
        api.send_message(user_id, "📝 میخوای متن هم اضافه بشه؟", reply_markup={
            "keyboard": [[{"text": "بله ✍️"}], [{"text": "خیر 🚀"}]],
            "resize_keyboard": True
        })
        return True

    except Exception as e:
        logger.error(f"❌ خطا در دریافت عکس: {e}", exc_info=True)
        return False


def handle_text_choice(user_id, choice):
    """انتخاب بله/خیر برای متن"""
    session = user_sessions.get(user_id)
    if not session:
        return

    if choice == "خیر 🚀":
        # بدون متن → مستقیم استیکر بساز
        finalize_sticker(user_id, session["image"], session["pack"])
        user_sessions.pop(user_id, None)

    elif choice == "بله ✍️":
        api.send_message(user_id, "✍️ متنتو بفرست تا بذارم روی استیکر.")


def handle_text_input(user_id, text):
    """گرفتن متن کاربر و اضافه کردن به استیکر"""
    session = user_sessions.get(user_id)
    if not session:
        return

    finalize_sticker(user_id, session["image"], session["pack"], text=text)
    user_sessions.pop(user_id, None)


def finalize_sticker(user_id, input_path, pack_name, text=None):
    """ساخت استیکر و ارسال با sendSticker"""
    try:
        ready_path = os.path.join(DATA_DIR, f"{user_id}_ready.png")
        resize_to_sticker_size(input_path, ready_path, text=text)

        # ✅ ارسال استیکر به کاربر
        api.send_sticker(user_id, ready_path)
        api.send_message(user_id, "✅ استیکرت آماده شد! میتونی سیوش کنی.")

    except Exception as e:
        logger.error(f"❌ خطا در ساخت استیکر: {e}", exc_info=True)
        api.send_message(user_id, "❌ خطا در ساخت استیکر. دوباره تلاش کن.")
