import os
import logging
from utils.telegram_api import TelegramAPI
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

api = TelegramAPI(token=os.getenv("TELEGRAM_BOT_TOKEN"))
DATA_DIR = "/tmp"   # مسیر ذخیره موقت عکس‌ها


def resize_to_sticker_size(input_path, output_path, text=None):
    """
    تغییر سایز عکس به 512x512 و اضافه کردن متن اختیاری
    """
    with Image.open(input_path).convert("RGBA") as im:
        im = im.resize((512, 512), Image.LANCZOS)

        if text:
            draw = ImageDraw.Draw(im)
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()

            # ✅ جایگزین textsize → استفاده از textbbox
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            pos = ((512 - text_w) // 2, 512 - text_h - 20)
            draw.text(pos, text, font=font, fill="white")

        im.save(output_path, "PNG")


def handle_sticker_upload(update, user_id, pack_name, text=None):
    """
    گرفتن عکس کاربر و ساختن/اضافه کردن استیکر به پک
    """
    try:
        message = update.get("message", {})
        photos = message.get("photo")
        if not photos:
            logger.error("❌ هیچ عکسی پیدا نشد.")
            return False

        # ✅ گرفتن بزرگ‌ترین سایز عکس
        file_id = photos[-1]["file_id"]
        logger.info(f"⬆️ دریافت عکس برای استیکر: user_id={user_id}, file_id={file_id}")

        # ✅ دانلود فایل
        raw_path = os.path.join(DATA_DIR, f"{user_id}_raw.png")
        ready_path = os.path.join(DATA_DIR, f"{user_id}_sticker.png")
        api.download_file(file_id, raw_path)

        # ✅ تغییر سایز + افزودن متن (اختیاری)
        resize_to_sticker_size(raw_path, ready_path, text=text)

        # ✅ ارسال مستقیم استیکر به کاربر (نه فقط پیام متن)
        with open(ready_path, "rb") as f:
            api.send_document(user_id, f, caption="✅ استیکرت آماده‌ست! ذخیره کن 📥")

        logger.info("✅ استیکر ساخته و برای کاربر ارسال شد.")
        return True

    except Exception as e:
        logger.error(f"❌ خطا در آپلود استیکر: {e}", exc_info=True)
        api.send_message(user_id, "❌ خطا در ساخت استیکر. دوباره تلاش کن.")
        return False


def reset_user_settings(user_id):
    """
    ریست کردن تنظیمات کاربر (مثلاً وقتی از نو شروع کنه)
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
