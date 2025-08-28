import os
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = os.environ.get("8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
API = f"https://api.telegram.org/bot{8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0}/"

app = Flask(name)

@app.route("/")
def home():
    return "Bot is running!"

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
    # پس‌زمینه سفید
    img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # فونت ساده (Railway فونت پیش‌فرض داره)
    font = ImageFont.load_default()

    # متن رو وسط بندازیم
    w, h = draw.textsize(text, font=font)
    draw.text(((512 - w) / 2, (512 - h) / 2), text, fill="black", font=font)

    img.save(path, "PNG")


if name == "main":
    port = int(os.environ.get("PORT", 8000))
    from waitress import serve
    serve(app, host="0.0.0.0", port=port)

    import os
from telegram.ext import Application, MessageHandler, filters

TOKEN = os.environ.get("BOT8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0")  # توکن رو از Railway می‌گیره

def main():
    if not TOKEN:
        raise ValueError("❌ BOT_TOKEN is not set! Go to Railway → Variables")

    app = Application.builder().token(TOKEN).build()

    async def echo(update, context):
        text = update.message.text
        await update.message.reply_text(f"Echo: {text}")

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Bot is running...")
    app.run_polling()

if name == "main":
    main()
