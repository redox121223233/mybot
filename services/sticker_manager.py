import os
import io
from PIL import Image, ImageDraw, ImageFont
import requests
from services.telegram_api import TelegramAPI

api = TelegramAPI(os.getenv("TELEGRAM_TOKEN"))

# ذخیره وضعیت کاربر
user_context = {}


def handle_sticker_upload(chat_id, file_id):
    """وقتی کاربر عکس می‌فرسته"""
    # فایل عکس رو از تلگرام دانلود کن
    file_info = api.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{api.token}/{file_info['file_path']}"
    response = requests.get(file_url)

    # ذخیره عکس در context
    user_context[chat_id] = {
        "photo": Image.open(io.BytesIO(response.content)),
        "awaiting_text": None
    }

    # سوال بپرس
    api.send_message(
        chat_id,
        "✍️ میخوای روی استیکرت متن هم بذارم؟",
        reply_markup={
            "keyboard": [[{"text": "بله ✍️"}], [{"text": "خیر 🚫"}]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
    )


def handle_text_choice(chat_id, text):
    """مدیریت جواب بله یا خیر"""
    ctx = user_context.get(chat_id)
    if not ctx:
        api.send_message(chat_id, "❌ اول یه عکس بفرست.")
        return

    text = text.strip()

    if text.startswith("بله"):
        ctx["awaiting_text"] = True
        api.send_message(chat_id, "✍️ خب! متنی که میخوای روی استیکر بیاد رو بفرست.")
    elif text.startswith("خیر"):
        ctx["awaiting_text"] = False
        make_and_send_sticker(chat_id, ctx["photo"])
    else:
        api.send_message(chat_id, "❌ متوجه نشدم. بله یا خیر رو انتخاب کن.")


def handle_text_input(chat_id, text):
    """وقتی کاربر متن استیکر رو فرستاد"""
    ctx = user_context.get(chat_id)
    if not ctx or ctx.get("awaiting_text") is not True:
        api.send_message(chat_id, "❌ اول باید بگی بله یا خیر.")
        return

    image = ctx["photo"]

    # فونت اضافه کن (یادت باشه فونت TTF رو توی پروژه بذاری مثل fonts/Vazir.ttf)
    try:
        font = ImageFont.truetype("fonts/Vazir.ttf", 48)
    except:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(image)
    w, h = image.size
    text_w, text_h = draw.textsize(text, font=font)

    # وسط بچین
    draw.text(((w - text_w) / 2, h - text_h - 20), text, font=font, fill="white")

    make_and_send_sticker(chat_id, image)


def make_and_send_sticker(chat_id, image):
    """عکس رو به استیکر تبدیل و ارسال کن"""
    bio = io.BytesIO()
    bio.name = "sticker.webp"
    image = image.convert("RGBA")
    image.save(bio, "WEBP")
    bio.seek(0)

    api.send_sticker(chat_id, bio)
    api.send_message(chat_id, "✅ استیکر ساخته شد!")
