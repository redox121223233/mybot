import os
import logging
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve
from io import BytesIO

# --- Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Config ---
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

    if not msg:
        return "ok"

    chat_id = msg["chat"]["id"]

    # متن
    if "text" in msg:
        text = msg["text"]

        if text == "/start":
            user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None}
            show_main_menu(chat_id)
            return "ok"

        if text == "🎁 تست رایگان":
            user_data[chat_id] = {"mode": "free", "count": 0, "step": "pack_name", "pack_name": None, "background": None}
            send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:")
            return "ok"

        state = user_data.get(chat_id, {})
        if state.get("mode") == "free":
            step = state.get("step")

            if step == "pack_name":
                pack_name = text.replace(" ", "_")
                user_data[chat_id]["pack_name"] = f"{pack_name}_by_{BOT_USERNAME}"
                user_data[chat_id]["step"] = "background"
                send_message(chat_id, "📷 حالا یک عکس برای بکگراند استیکرت بفرست:")
                return "ok"

            if step == "text":
                text_sticker = text
                send_message(chat_id, "⚙️ در حال ساخت استیکر...")
                background_file_id = user_data[chat_id].get("background")
                send_as_sticker(chat_id, text_sticker, background_file_id)
                user_data[chat_id]["count"] += 1
                send_message(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد.")
                return "ok"

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

    elif "photo" in msg:
        state = user_data.get(chat_id, {})
        if state.get("mode") == "free" and state.get("step") == "background":
            file_id = msg["photo"][-1]["file_id"]
            user_data[chat_id]["background"] = file_id
            user_data[chat_id]["step"] = "text"
            send_message(chat_id, "✍️ حالا متن استیکرت رو بفرست:")
            return "ok"

    return "ok"

def send_as_sticker(chat_id, text, background_file_id=None):
    sticker_path = "sticker.png"
    ok = make_text_sticker(text, sticker_path, background_file_id)
    if not ok:
        send_message(chat_id, "❌ خطا در ساخت استیکر")
        return

    pack_name = user_data[chat_id].get("pack_name", f"pack{abs(chat_id)}_by_{BOT_USERNAME}")
    pack_title = f"Sticker Pack {chat_id}"

    # بررسی اینکه آیا پک استیکر وجود داره یا نه
    resp = requests.get(API + f"getStickerSet?name={pack_name}").json()

    if not resp.get("ok"):
        send_message(chat_id, f"آیا می‌خواهید پک جدید بسازید یا استیکر جدید به پک قبلی اضافه شود؟\n 1. ساخت پک جدید\n 2. اضافه کردن به پک قبلی")
        user_data[chat_id]["step"] = "pack_choice"
        return "ok"
    else:
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": chat_id,
                "name": pack_name,
                "emojis": "🔥"
            }
            r = requests.post(API + "addStickerToSet", data=data, files=files)
            logger.info(f"Add sticker resp: {r.json()}")

    final = requests.get(API + f"getStickerSet?name={pack_name}").json()
    if final.get("ok"):
        stickers = final["result"]["stickers"]
        if stickers:
            file_id = stickers[-1]["file_id"]
            requests.post(API + "sendSticker", data={"chat_id": chat_id, "sticker": file_id})

def make_text_sticker(text, path, background_file_id=None):
    try:
        img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))

        draw = ImageDraw.Draw(img)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        # شروع از سایز بزرگ و کم‌کردن تا جا بشه
        font_size = 400
        while font_size > 50:
            try:
                font = ImageFont.truetype(font_path, font_size)
            except OSError:
                font = ImageFont.load_default()
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except AttributeError:
                w, h = draw.textsize(text, font=font)
            if w <= 480 and h <= 480:
                break
            font_size -= 10

        x = (512 - w) / 2
        y = (512 - h) / 2

        # حاشیه سفید
        outline_range = 10
        for dx in range(-outline_range, outline_range + 1, 2):
            for dy in range(-outline_range, outline_range + 1, 2):
                draw.text((x+dx, y+dy), text, font=font, fill="white")

        draw.text((x, y), text, fill="black", font=font)
        img.save(path, "PNG")
        return True
    except Exception as e:
        logger.error(f"make_text_sticker error: {e}")
        return False

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
        logger.info(f"setWebhook: {resp.json()}")
    else:
        logger.warning("⚠️ APP_URL is not set. Webhook not registered.")

    port = int(os.environ.get("PORT", 8000))
    serve(app, host="0.0.0.0", port=port)
