import os
import logging
import requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont

# 📌 کتابخونه‌های لازم برای فارسی
import arabic_reshaper
from bidi.algorithm import get_display

# ------------------ تنظیمات ------------------ #
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

app = Flask(__name__)

# ------------------ کمک‌کننده ------------------ #
def reshape_text(text: str) -> str:
    """اصلاح متن فارسی برای رندر درست"""
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    return bidi_text

def get_font(size=80, language="english"):
    """بارگذاری فونت مناسب"""
    if language == "persian":
        font_paths = [
            "Vazirmatn-black.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    else:
        font_paths = [
            "arial.ttf",
            "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    return ImageFont.load_default()

def make_text_sticker(text, path, language="persian", background=None):
    """ساخت استیکر متنی (با بکگراند یا بدون)"""
    size = (512, 512)

    if background:
        img = Image.open(background).convert("RGBA").resize(size)
    else:
        img = Image.new("RGBA", size, (255, 255, 255, 0))

    draw = ImageDraw.Draw(img)

    # ✅ اصلاح متن فارسی
    if language == "persian":
        text = reshape_text(text)

    font = get_font(120, language)

    # محاسبه جای درست متن
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = (size[0] - w) // 2, (size[1] - h) // 2

    # سایه سیاه پشت متن
    draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 255))
    # متن سفید
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    img.save(path, "PNG")

# ------------------ هندل وبهوک ------------------ #
@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json()
    if not update:
        return "ok"

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg:
            text = msg["text"]
            if text.startswith("/start"):
                send_message(chat_id, "سلام 👋 متن استیکرت رو بفرست:")
            else:
                sticker_path = f"/tmp/sticker_{chat_id}.png"
                make_text_sticker(text, sticker_path, language="persian")
                send_sticker(chat_id, sticker_path)

    return "ok"

# ------------------ ارسال به تلگرام ------------------ #
def send_message(chat_id, text):
    requests.post(API + "sendMessage", json={"chat_id": chat_id, "text": text})

def send_sticker(chat_id, sticker_path):
    with open(sticker_path, "rb") as f:
        requests.post(API + "sendSticker", data={"chat_id": chat_id}, files={"sticker": f})

# ------------------ اجرا ------------------ #
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
