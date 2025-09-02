import os
import logging
import requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ---------------- تنظیمات ---------------- #
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
SUPPORT_ID = os.getenv("SUPPORT_ID", "@YourSupport")
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

FONT_PATH = os.path.join(os.path.dirname(__file__), "Vazirmatn-Regular.ttf")

# دیتای ساده برای مدیریت یوزرها (در عمل بهتره DB باشه)
user_data = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")
app = Flask(__name__)

# ---------------- کمکی ---------------- #
def reshape_text(text: str) -> str:
    """اصلاح متن فارسی"""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

def get_font(size=120):
    """لود فونت Vazirmatn"""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception as e:
        logger.error(f"❌ فونت لود نشد: {e}")
        return ImageFont.load_default()

def make_text_sticker(text, path, is_persian=True, background=None):
    """ساخت استیکر با متن و بکگراند اختیاری"""
    size = (512, 512)

    if background:
        img = Image.open(background).convert("RGBA").resize(size)
    else:
        img = Image.new("RGBA", size, (255, 255, 255, 0))

    draw = ImageDraw.Draw(img)

    if is_persian:
        text = reshape_text(text)

    font_size = 200
    font = get_font(font_size)

    # کاهش سایز تا متن جا بشه
    while True:
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= size[0] - 40 and h <= size[1] - 40:
            break
        font_size -= 10
        font = get_font(font_size)

    x, y = (size[0] - w) // 2, (size[1] - h) // 2

    # سایه مشکی
    draw.text((x+4, y+4), text, font=font, fill="black")
    # متن سفید
    draw.text((x, y), text, font=font, fill="white")

    img.save(path, "PNG")

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(API + "sendMessage", json=payload)

def send_sticker(chat_id, sticker_path):
    with open(sticker_path, "rb") as f:
        requests.post(API + "sendSticker", data={"chat_id": chat_id}, files={"sticker": f})

# ---------------- هندل وبهوک ---------------- #
@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "ok"

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        # اگر متن بود
        if "text" in msg:
            text = msg["text"]

            if text.startswith("/start"):
                keyboard = {
                    "keyboard": [
                        [{"text": "🎁 تست رایگان"}],
                        [{"text": "⭐ اشتراک"}],
                        [{"text": "📞 پشتیبانی"}]
                    ],
                    "resize_keyboard": True
                }
                send_message(chat_id, "سلام 👋 یکی از گزینه‌ها رو انتخاب کن:", reply_markup=keyboard)

            elif text == "📞 پشتیبانی":
                send_message(chat_id, f"برای پشتیبانی به {SUPPORT_ID} پیام بده.")

            elif text == "🎁 تست رایگان":
                user = user_data.get(chat_id, {"free_used": 0, "subscribed": False})
                if user["free_used"] >= 5 and not user["subscribed"]:
                    send_message(chat_id, "❌ سقف استفاده رایگان تموم شد. لطفاً اشتراک بگیر ⭐")
                else:
                    user_data[chat_id] = user
                    user["mode"] = "waiting_text"
                    send_message(chat_id, "متنی که میخوای استیکر بشه رو بفرست:")

            elif text == "⭐ اشتراک":
                user = user_data.get(chat_id, {"free_used": 0, "subscribed": False})
                user["subscribed"] = True
                user_data[chat_id] = user
                send_message(chat_id, "✅ اشتراک فعال شد! الان می‌تونی نامحدود استیکر بسازی.")

            else:
                user = user_data.get(chat_id)
                if user and user.get("mode") == "waiting_text":
                    user["mode"] = None
                    is_persian = any("ا" <= ch <= "ی" for ch in text)
                    sticker_path = f"/tmp/sticker_{chat_id}.png"
                    make_text_sticker(text, sticker_path, is_persian=is_persian)
                    send_sticker(chat_id, sticker_path)
                    if not user["subscribed"]:
                        user["free_used"] += 1

        # اگر عکس بود
        elif "photo" in msg:
            file_id = msg["photo"][-1]["file_id"]
            file_info = requests.get(API + f"getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            local_path = f"/tmp/{chat_id}_bg.png"
            with open(local_path, "wb") as f:
                f.write(requests.get(file_url).content)

            user = user_data.get(chat_id)
            if user and user.get("mode") == "waiting_text":
                # ذخیره عکس به عنوان بکگراند
                user["background"] = local_path
                send_message(chat_id, "✅ عکس بکگراند ذخیره شد. حالا متن رو بفرست:")

    return "ok"

# ---------------- اجرا ---------------- #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
