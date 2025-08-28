import os
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve

# گرفتن توکن از متغیر محیطی
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set! Please add it in Railway → Variables")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
APP_URL = os.environ.get("APP_URL")  # اینو باید توی Railway بذاری
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

    font = ImageFont.load_default()
    w, h = draw.textsize(text, font=font)
    draw.text(((512 - w) / 2, (512 - h) / 2), text, fill="black", font=font)

    img.save(path, "PNG")


if __name__ == "__main__":
    # اول Webhook رو ست کنه
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        resp = requests.get(API + f"setWebhook?url={webhook_url}")
        print("DEBUG setWebhook:", resp.json())
    else:
        print("⚠️ APP_URL is not set in Railway → Variables")

    # اجرا روی Railway
    port = int(os.environ.get("PORT", 8000))
    serve(app, host="0.0.0.0", port=port)
