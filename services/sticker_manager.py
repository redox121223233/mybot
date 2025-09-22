import os
import logging
from utils.telegram_api import TelegramAPI
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

api = TelegramAPI(token=os.getenv("BOT_TOKEN"))
DATA_DIR = "/tmp"   # مسیر ذخیره موقت عکس‌ها


def resize_to_sticker_size(input_path, output_path, text=None):
    """
    تغییر اندازه تصویر به 512x512 و نوشتن متن روی آن (اختیاری)
    """
    with Image.open(input_path) as img:
        img = img.convert("RGBA")
        img = img.resize((512, 512), Image.LANCZOS)

        if text:
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 36)
            except:
                font = ImageFont.load_default()

            # وسط چین
            text_w, text_h = draw.textsize(text, font=font)
            x = (img.width - text_w) // 2
            y = img.height - text_h - 10
            draw.text((x, y), text, font=font, fill="white")

        img.save(output_path, format="PNG")


def handle_sticker_upload(update, user_id, pack_name, text=None):
    """
    گرفتن عکس کاربر و ساختن/اضافه کردن استیکر به پک + ارسال به کاربر (send_sticker)
    """
    try:
        if not isinstance(update, dict):
            logger.error(f"❌ update دیکشنری نیست: {type(update)}")
            return False

        message = update.get("message", {})
        photos = message.get("photo")
        if not photos:
            logger.error("❌ هیچ عکسی پیدا نشد.")
            return False

        # ✅ گرفتن بزرگ‌ترین سایز عکس
        file_id = photos[-1]["file_id"]
        logger.info(f"⬆️ دریافت عکس برای استیکر: user_id={user_id}, file_id={file_id}")

        # ✅ دانلود فایل
        dest_path = os.path.join(DATA_DIR, f"{user_id}_sticker.png")
        api.download_file(file_id, dest_path)

        # ✅ تغییر سایز و نوشتن متن
        resized_path = os.path.join(DATA_DIR, f"{user_id}_sticker_ready.png")
        resize_to_sticker_size(dest_path, resized_path, text=text)

        bot_username = "matnsticker_bot"
        full_pack_name = f"{pack_name}_by_{bot_username}"

        # ✅ ساخت یا اضافه کردن استیکر
        if not api.sticker_set_exists(full_pack_name):
            api.create_new_sticker_set(
                user_id=user_id,
                name=full_pack_name,
                title=f"Sticker Pack by {user_id}",
                png_path=resized_path,
                emoji="😀"
            )
        else:
            api.add_sticker_to_set(
                user_id=user_id,
                name=full_pack_name,
                png_path=resized_path,
                emoji="😀"
            )

        # ✅ ارسال استیکر به کاربر (نه فایل PNG)
        api.send_sticker(user_id, resized_path)

        logger.info("✅ استیکر ساخته و برای کاربر ارسال شد (send_sticker).")
        return True

    except Exception as e:
        logger.error(f"❌ خطا در آپلود استیکر: {e}", exc_info=True)
        api.send_message(user_id, "❌ خطا در ساخت استیکر. دوباره تلاش کن.")
        return False
