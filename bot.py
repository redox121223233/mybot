import os
import logging
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve
from io import BytesIO

# --- Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# --- Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set!")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
APP_URL = os.environ.get("APP_URL")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")  # username ربات بدون @
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

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

    if "text" in msg:
        text = msg["text"]

        if text == "/start":
            user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None}
            show_main_menu(chat_id)
            return "ok"

        if text == "🎁 تست رایگان":
            user_data[chat_id] = {"mode": "free", "count": 0, "step": "ask_pack_choice", "pack_name": None, "background": None}
            send_message(chat_id, "📝 آیا می‌خواهید پک جدید بسازید یا به پک قبلی اضافه کنید؟\n1. ساخت پک جدید\n2. اضافه کردن به پک قبلی")
            return "ok"

        state = user_data.get(chat_id, {})
        if state.get("mode") == "free":
            step = state.get("step")

            if step == "ask_pack_choice":
                if text == "1":
                    send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:")
                    user_data[chat_id]["step"] = "pack_name"
                elif text == "2":
                    if user_data[chat_id].get("pack_name"):
                        send_message(chat_id, "📷 یک عکس برای بکگراند استیکرت بفرست:")
                        user_data[chat_id]["step"] = "background"
                    else:
                        send_message(chat_id, "❌ هنوز پک استیکری نداری. اول باید پک جدید بسازی.")
                return "ok"

            if step == "pack_name":
                pack_name = text.replace(" ", "_")
                user_data[chat_id]["pack_name"] = f"{pack_name}_by_{BOT_USERNAME}"
                send_message(chat_id, "📷 یک عکس برای بکگراند استیکرت بفرست:")
                user_data[chat_id]["step"] = "background"
                return "ok"

            if step == "text":
                text_sticker = text
                send_message(chat_id, "⚙️ در حال ساخت استیکر...")
                background_file_id = user_data[chat_id].get("background")
                send_as_sticker(chat_id, text_sticker, background_file_id)
                user_data[chat_id]["count"] += 1
                send_message(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد.")
                return "ok"

    elif "photo" in msg:
        state = user_data.get(chat_id, {})
        if state.get("mode") == "free" and state.get("step") == "background":
            photos = msg.get("photo", [])
            if photos:
                file_id = photos[-1].get("file_id")
                if file_id:
                    user_data[chat_id]["background"] = file_id
                    user_data[chat_id]["step"] = "text"
                    send_message(chat_id, "✍️ حالا متن استیکرت رو بفرست:")

    return "ok"

# ======================
# استیکر سازی
# ======================
def get_font(size, language="english"):
    """بارگذاری فونت - اولویت با Vazirmatn برای فارسی"""
    if language == "persian":
        font_paths = [
            "Vazirmatn-Regular.ttf",    # 📌 اسم دقیق فایل
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
    else:
        font_paths = [
            "arial.ttf",
            "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        ]

    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, size)
            logger.info(f"Loaded font: {font_path}")
            return font
        except:
            continue

    return ImageFont.load_default()

def detect_language(text):
    for ch in text:
        if '\u0600' <= ch <= '\u06FF':
            return "persian"
    return "english"

def make_text_sticker(text, path, background_file_id=None):
    try:
        language = detect_language(text)
        base_size = 512
        img = Image.new("RGBA", (base_size, base_size), (255, 255, 255, 0))

        if background_file_id:
            try:
                file_info = requests.get(API + f"getFile?file_id={background_file_id}").json()
                if file_info.get("ok"):
                    file_path = file_info["result"]["file_path"]
                    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                    resp = requests.get(file_url)
                    if resp.status_code == 200:
                        bg = Image.open(BytesIO(resp.content)).convert("RGBA")
                        bg = bg.resize((base_size, base_size))
                        img.paste(bg, (0, 0))
            except Exception as e:
                logger.error(f"Error loading background: {e}")

        draw = ImageDraw.Draw(img)

        font_size = 400
        font = get_font(font_size, language)

        while True:
            bbox = draw.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if w <= base_size - 20 and h <= base_size - 20:
                break
            font_size -= 10
            font = get_font(font_size, language)

        x = (base_size - w) / 2
        y = (base_size - h) / 2

        outline_thickness = max(3, font_size // 20)
        for dx in range(-outline_thickness, outline_thickness + 1):
            for dy in range(-outline_thickness, outline_thickness + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill="white")

        draw.text((x, y), text, font=font, fill="black")

        img.save(path, "PNG")
        return True
    except Exception as e:
        logger.error(f"make_text_sticker error: {e}")
        return False

def send_as_sticker(chat_id, text, background_file_id=None):
    sticker_path = "sticker.png"
    ok = make_text_sticker(text, sticker_path, background_file_id)
    if not ok:
        send_message(chat_id, "❌ خطا در ساخت استیکر")
        return

    pack_name = user_data[chat_id].get("pack_name", f"pack{abs(chat_id)}_by_{BOT_USERNAME}")
    pack_title = f"Sticker Pack {chat_id}"

    resp = requests.get(API + f"getStickerSet?name={pack_name}").json()
    if not resp.get("ok"):
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {"user_id": chat_id, "name": pack_name, "title": pack_title, "emojis": "🔥"}
            requests.post(API + "createNewStickerSet", data=data, files=files)
    else:
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {"user_id": chat_id, "name": pack_name, "emojis": "🔥"}
            requests.post(API + "addStickerToSet", data=data, files=files)

    final = requests.get(API + f"getStickerSet?name={pack_name}").json()
    if final.get("ok"):
        stickers = final["result"]["stickers"]
        if stickers:
            file_id = stickers[-1]["file_id"]
            requests.post(API + "sendSticker", data={"chat_id": chat_id, "sticker": file_id})

# ======================
# Helpers
# ======================
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
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
