import os
import logging
from utils.telegram_api import TelegramAPI
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# 📌 گرفتن توکن از محیط (نه از config.py)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("❌ متغیر محیطی TELEGRAM_TOKEN تنظیم نشده!")

api = TelegramAPI(TELEGRAM_TOKEN)
DATA_DIR = "/tmp"   # مسیر ذخیره موقت


# 📌 تغییر سایز به استاندارد استیکر (512px) + نوشتن متن در صورت نیاز
def resize_to_sticker_size(input_path, output_path, text=None):
    img = Image.open(input_path).convert("RGBA")

    # تغییر سایز به 512px
    max_size = 512
    img.thumbnail((max_size, max_size), Image.LANCZOS)

    if text:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = ImageFont.load_default()

        # محاسبه سایز متن
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # محل متن پایین وسط
        x = (img.width - text_w) // 2
        y = img.height - text_h - 10

        # سایه مشکی
        draw.text((x+2, y+2), text, font=font, fill="black")
        # متن سفید
        draw.text((x, y), text, font=font, fill="white")

    img.save(output_path, "PNG")
    return output_path


# 📌 ذخیره عکس و آماده‌سازی برای استیکر
def handle_sticker_upload(update, user_id, pack_name, text=None):
    try:
        message = update.get("message", {})
        photos = message.get("photo")
        if not photos:
            logger.error("❌ هیچ عکسی پیدا نشد.")
            return False

        file_id = photos[-1]["file_id"]
        logger.info(f"⬆️ دریافت عکس: user_id={user_id}, file_id={file_id}")

        raw_path = os.path.join(DATA_DIR, f"{user_id}_raw.png")
        ready_path = os.path.join(DATA_DIR, f"{user_id}_sticker.png")

        # دانلود فایل
        api.download_file(file_id, raw_path)

        # تغییر سایز و نوشتن متن
        resize_to_sticker_size(raw_path, ready_path, text=text)

        # فرستادن به کاربر به عنوان عکس (که بتونه سیو کنه)
        api.send_photo(user_id, ready_path, caption="✅ استیکرت آماده شد!")

        return True

    except Exception as e:
        logger.error(f"❌ خطا در ساخت استیکر: {e}", exc_info=True)
        api.send_message(user_id, "❌ خطا در ساخت استیکر. دوباره تلاش کن.")
        return False


# 📌 هندل کردن انتخاب کاربر (بله/خیر)
def handle_text_choice(update, user_id, pack_name):
    text = update["message"].get("text")
    if text == "بله ✍️":
        api.send_message(user_id, "✍️ متنتو بفرست تا بذارم روی استیکر.")
        return "awaiting_text"
    elif text == "خیر 🚫":
        return handle_sticker_upload(update, user_id, pack_name)
    else:
        api.send_message(user_id, "❌ متوجه نشدم. بله یا خیر رو انتخاب کن.")
        return None


# 📌 هندل کردن متن وارد شده توسط کاربر
def handle_text_input(update, user_id, pack_name):
    text = update["message"].get("text")
    return handle_sticker_upload(update, user_id, pack_name, text=text)
