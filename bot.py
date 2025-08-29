import os
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set!")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
APP_URL = os.environ.get("APP_URL")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")  # یوزرنیم ربات (بدون @)
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# دیتابیس ساده
user_data = {}

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

        # ریست و منو
        if text == "/start":
            user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None}
            show_main_menu(chat_id)
            return "ok"

        # گزینه تست رایگان
        if text == "🎁 تست رایگان":
            user_data[chat_id] = {"mode": "free", "count": 0, "step": "pack_name", "pack_name": None, "background": None}
            send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:")
            return "ok"

        # دریافت مراحل ساخت پک رایگان
        state = user_data.get(chat_id, {})
        if state.get("mode") == "free":
            step = state.get("step")

            if step == "pack_name":
                # ذخیره نام پک
                pack_name = text.replace(" ", "_")
                user_data[chat_id]["pack_name"] = f"{pack_name}_by_{BOT_USERNAME}"
                user_data[chat_id]["step"] = "background"
                send_message(chat_id, "📷 حالا یک عکس برای بکگراند استیکرت بفرست:")
                return "ok"

            if step == "background" and "photo" in msg:
                # دریافت عکس بکگراند
                file_id = msg["photo"][-1]["file_id"]
                user_data[chat_id]["background"] = file_id
                user_data[chat_id]["step"] = "text"
                send_message(chat_id, "✍️ حالا متن استیکرت رو بفرست:")
                return "ok"

            if step == "text":
                text_sticker = text
                send_message(chat_id, "⚙️ در حال ساخت استیکر...")
                send_as_sticker(chat_id, text_sticker)
                user_data[chat_id]["count"] += 1
                send_message(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد.")
                return "ok"

        # سایر گزینه‌ها
        if text == "⭐ اشتراک":
            send_message(chat_id, "💳 بخش اشتراک بعداً فعال خواهد شد.")
            return "ok"

        elif text == "📂 پک من":
            pack_name = user_data.get(chat_id, {}).get("pack_name")
            if pack_name:
                pack_url = f"https://t.me/addstickers/{pack_name}"
                send_message(chat_id, f"🗂 پک استیکرت اینجاست:\n{pack_url}")
            else:
                send_message(chat_id, "❌ هنوز پکی برایت ساخته نشده.")
            return "ok"

        elif text == "ℹ️ درباره":
            send_message(chat_id, "ℹ️ این ربات برای ساخت استیکر متنی است. نسخه فعلی رایگان است.")
            return "ok"

        elif text == "📞 پشتیبانی":
            support_id = os.environ.get("SUPPORT_ID", "@YourSupportID")
            send_message(chat_id, f"📞 برای پشتیبانی با {support_id} در تماس باش.")
            return "ok"

    return "ok"

def send_as_sticker(chat_id, text):
    sticker_path = "sticker.png"
    make_text_sticker(text, sticker_path)

    pack_name = user_data[chat_id].get("pack_name", f"pack{abs(chat_id)}_by_{BOT_USERNAME}")
    pack_title = f"Sticker Pack {chat_id}"

    resp = requests.get(API + f"getStickerSet?name={pack_name}").json()

    if not resp.get("ok"):
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": chat_id,
                "name": pack_name,
                "title": pack_title,
                "emojis": "🔥"
            }
            requests.post(API + "createNewStickerSet", data=data, files=files)
    else:
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": chat_id,
                "name": pack_name,
                "emojis": "🔥"
            }
            requests.post(API + "addStickerToSet", data=data, files=files)

    final = requests.get(API + f"getStickerSet?name={pack_name}").json()
    if final.get("ok"):
        stickers = final["result"]["stickers"]
        if stickers:
            file_id = stickers[-1]["file_id"]
            requests.post(API + "sendSticker", data={"chat_id": chat_id, "sticker": file_id})

def make_text_sticker(text, path):
    img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    font_path = os.environ.get("FONT_PATH", "Vazir.ttf")

    size = 200
    try:
        font = ImageFont.truetype(font_path, size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((512 - w) / 2, (512 - h) / 2), text, fill="black", font=font)

    img.save(path, "PNG")

def show_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🎁 تست رایگان", "⭐ اشتراک"],
            ["📂 پک من", "ℹ️ درباره"],
            ["📞 پشتیبانی"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "👋 خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:",
        "reply_markup": keyboard
    })

def send_message(chat_id, text):
    requests.post(API + "sendMessage", json={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        resp = requests.get(API + f"setWebhook?url={webhook_url}")
        print("DEBUG setWebhook:", resp.json())

    port = int(os.environ.get("PORT", 8000))
    serve(app, host="0.0.0.0", port=port)
