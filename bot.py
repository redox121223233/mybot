import os
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve

# گرفتن توکن از متغیر محیطی (Railway → Variables)
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# دیباگ: چاپ توکن
print("DEBUG BOT_TOKEN:", repr(BOT_TOKEN))  # مقدار واقعی رو توی لاگ Railway ببین

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set! Please add it in Railway → Variables")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

app = Flask(__name__)


@app.route("/")
def home():
    return "✅ Bot is running!"


@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    msg = update.get("message")
    if msg and "text" in msg:
        chat_id = msg["chat"]["id"]
        text = msg["text"]

        # ساخت استیکر (تصویر با متن)
        sticker_path = "sticker.png"
        make_text_sticker(text, sticker_path)

        # آپلود عکس به تلگرام به صورت استیکر
        with open(sticker_path, "rb") as f:
            requests.post(
                API + "sendSticker",
                data={"chat_id": chat_id},
                files={"sticker": f},
            )

    return "ok"


def make_text_sticker(text, path):
    """ساخت تصویر ساده با متن"""
    img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # فونت ساده
    font = ImageFont.load_default()

    # متن وسط
    w, h = draw.textsize(text, font=font)
    draw.text(((512 - w) / 2, (512 - h) / 2), text, fill="black", font=font)

    img.save(path, "PNG")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    serve(app, host="0.0.0.0", port=port)
