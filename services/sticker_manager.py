import os
import logging
from PIL import Image, ImageDraw, ImageFont
from utils.telegram_api import TelegramAPI
from config import TELEGRAM_TOKEN

logger = logging.getLogger(__name__)

api = TelegramAPI(TELEGRAM_TOKEN)
DATA_DIR = "/tmp"

# حافظه موقت وضعیت کاربران
USER_STATE = {}


def resize_to_sticker_size(input_path, output_path, text=None):
    """
    تغییر اندازه تصویر به ابعاد مجاز استیکر تلگرام + افزودن متن در صورت نیاز
    """
    with Image.open(input_path).convert("RGBA") as img:
        # تغییر اندازه به ابعاد مجاز (512x512)
        img.thumbnail((512, 512))

        if text:
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except:
                logger.warning("⚠️ فونت arial.ttf پیدا نشد. استفاده از پیش‌فرض.")
                font = ImageFont.load_default()

            # اندازه متن
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (img.width - text_w) // 2
            y = img.height - text_h - 10
            draw.text((x, y), text, font=font, fill="white")

        img.save(output_path, "PNG")


def handle_sticker_upload(update, user_id, pack_name, text=None):
    """
    گرفتن عکس کاربر و ذخیره موقت برای ساخت استیکر
    """
    try:
        message = update.get("message", {})
        photos = message.get("photo")
        if not photos:
            logger.error("❌ هیچ عکسی پیدا نشد.")
            return False

        # ✅ بزرگ‌ترین سایز عکس
        file_id = photos[-1]["file_id"]
        logger.info(f"⬆️ دریافت عکس برای استیکر: user_id={user_id}, file_id={file_id}")

        dest_path = os.path.join(DATA_DIR, f"{user_id}_raw.png")
        api.download_file(file_id, dest_path)

        # بعد از ذخیره عکس از کاربر بپرسیم که متن می‌خواد یا نه
        keyboard = {
            "keyboard": [[{"text": "بله ✍️"}], [{"text": "خیر 🚫"}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        }
        api.send_message(user_id, "❓ میخوای روی استیکرت متن هم بذاری؟", reply_markup=keyboard)
        return True

    except Exception as e:
        logger.error(f"❌ خطا در آپلود استیکر: {e}", exc_info=True)
        return False


def handle_text_choice(user_id, text):
    """
    بررسی انتخاب کاربر بعد از آپلود عکس (آیا متن اضافه کند یا نه؟)
    """
    if text.strip() == "بله ✍️":
        USER_STATE[user_id] = "awaiting_text"
        api.send_message(user_id, "✍️ متنتو بفرست تا بذارم روی استیکر.")
        return True

    elif text.strip() == "خیر 🚫":
        raw_path = os.path.join(DATA_DIR, f"{user_id}_raw.png")
        ready_path = os.path.join(DATA_DIR, f"{user_id}_sticker.png")
        resize_to_sticker_size(raw_path, ready_path, text=None)
        with open(ready_path, "rb") as f:
            api.send_document(user_id, f, caption="✅ استیکرت آماده‌ست! ذخیره کن 📥")
        return True

    return False


def handle_text_input(user_id, text):
    """
    دریافت متن کاربر و ساخت استیکر با متن
    """
    if USER_STATE.get(user_id) == "awaiting_text":
        raw_path = os.path.join(DATA_DIR, f"{user_id}_raw.png")
        ready_path = os.path.join(DATA_DIR, f"{user_id}_sticker.png")
        resize_to_sticker_size(raw_path, ready_path, text=text)
        with open(ready_path, "rb") as f:
            api.send_document(user_id, f, caption="✅ استیکرت آماده‌ست با متن 📥")
        USER_STATE.pop(user_id, None)
        return True

    return False


def reset_user_settings(user_id):
    """
    ریست کردن تنظیمات کاربر
    """
    try:
        settings_path = os.path.join(DATA_DIR, f"{user_id}_settings.json")
        if os.path.exists(settings_path):
            os.remove(settings_path)
            logger.info(f"🔄 تنظیمات کاربر {user_id} ریست شد.")
        return True
    except Exception as e:
        logger.error(f"❌ خطا در ریست تنظیمات کاربر {user_id}: {e}", exc_info=True)
        return False
