import os
import logging
import re
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve
from io import BytesIO
import arabic_reshaper
from bidi.algorithm import get_display

# --- Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# --- Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set!")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
APP_URL = os.environ.get("APP_URL")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")  # یوزرنیم ربات بدون @
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# دیتابیس ساده در حافظه
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

    # 📌 پردازش متن
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
                if text == "1":  # ساخت پک جدید
                    send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:")
                    user_data[chat_id]["step"] = "pack_name"
                elif text == "2":  # اضافه کردن به پک قبلی
                    pack_name = user_data[chat_id].get("pack_name")
                    if pack_name:
                        # بررسی اینکه پک واقعاً وجود دارد یا نه
                        resp = requests.get(API + f"getStickerSet?name={pack_name}").json()
                        if resp.get("ok"):
                            send_message(chat_id, "📷 یک عکس برای بکگراند استیکرت بفرست:")
                            user_data[chat_id]["step"] = "background"
                        else:
                            send_message(chat_id, "❌ پک قبلی پیدا نشد. لطفاً پک جدید بسازید.")
                            user_data[chat_id]["step"] = "pack_name"
                            send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:")
                    else:
                        send_message(chat_id, "❌ هنوز پک استیکری نداری. اول باید پک جدید بسازی.")
                        user_data[chat_id]["step"] = "pack_name"
                        send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:")
                return "ok"

            if step == "pack_name":
                pack_name = text.replace(" ", "_")
                full_pack_name = f"{pack_name}_by_{BOT_USERNAME}"
                
                # بررسی اینکه پک با این نام وجود دارد یا نه
                resp = requests.get(API + f"getStickerSet?name={full_pack_name}").json()
                if resp.get("ok"):
                    send_message(chat_id, f"❌ پک با نام '{pack_name}' از قبل وجود دارد. لطفاً نام دیگری انتخاب کنید:")
                    return "ok"
                
                user_data[chat_id]["pack_name"] = full_pack_name
                send_message(chat_id, "📷 یک عکس برای بکگراند استیکرت بفرست:")
                user_data[chat_id]["step"] = "background"
                return "ok"

            if step == "text":
                text_sticker = text
                send_message(chat_id, "⚙️ در حال ساخت استیکر...")
                background_file_id = user_data[chat_id].get("background")
                send_as_sticker(chat_id, text_sticker, background_file_id)
                user_data[chat_id]["count"] += 1
                
                # 🔥 مهم: بعد از ساخت استیکر، state را برای استیکر بعدی آماده کن
                send_message(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد.\n\n✍️ متن استیکر بعدی را بفرست:")
                # step همچنان "text" باقی می‌ماند تا کاربر بتواند استیکر بعدی بسازد
                return "ok"

        # دکمه‌های منو
        if text == "⭐ اشتراک":
            send_message(chat_id, "💳 بخش اشتراک بعداً فعال خواهد شد.")
        elif text == "📂 پک من":
            pack_name = user_data.get(chat_id, {}).get("pack_name")
            if pack_name:
                # بررسی اینکه پک واقعاً وجود دارد
                resp = requests.get(API + f"getStickerSet?name={pack_name}").json()
                if resp.get("ok"):
                    pack_url = f"https://t.me/addstickers/{pack_name}"
                    send_message(chat_id, f"🗂 پک استیکرت اینجاست:\n{pack_url}")
                else:
                    send_message(chat_id, "❌ هنوز پکی برایت ساخته نشده.")
            else:
                send_message(chat_id, "❌ هنوز پکی برایت ساخته نشده.")
        elif text == "ℹ️ درباره":
            send_message(chat_id, "ℹ️ این ربات برای ساخت استیکر متنی است. نسخه فعلی رایگان است.")
        elif text == "📞 پشتیبانی":
            support_id = os.environ.get("SUPPORT_ID", "@YourSupportID")
            send_message(chat_id, f"📞 برای پشتیبانی با {support_id} در تماس باش.")

    # 📌 پردازش عکس
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

def send_as_sticker(chat_id, text, background_file_id=None):
    sticker_path = "sticker.png"
    ok = make_text_sticker(text, sticker_path, background_file_id)
    if not ok:
        send_message(chat_id, "❌ خطا در ساخت استیکر")
        return

    pack_name = user_data[chat_id].get("pack_name")
    if not pack_name:
        send_message(chat_id, "❌ خطا: نام پک تعریف نشده")
        return
        
    pack_title = f"Sticker Pack {chat_id}"

    resp = requests.get(API + f"getStickerSet?name={pack_name}").json()

    if not resp.get("ok"):  # اگر پک وجود نداشت، اول باید ساخته بشه
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": chat_id,
                "name": pack_name,
                "title": pack_title,
                "emojis": "🔥"
            }
            r = requests.post(API + "createNewStickerSet", data=data, files=files)
            logger.info(f"Create sticker resp: {r.json()}")
    else:  # پک هست → استیکر جدید اضافه کن
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": chat_id,
                "name": pack_name,
                "emojis": "🔥"
            }
            r = requests.post(API + "addStickerToSet", data=data, files=files)
            logger.info(f"Add sticker resp: {r.json()}")

    # ارسال استیکر به کاربر
    final = requests.get(API + f"getStickerSet?name={pack_name}").json()
    if final.get("ok"):
        stickers = final["result"]["stickers"]
        if stickers:
            file_id = stickers[-1]["file_id"]
            requests.post(API + "sendSticker", data={"chat_id": chat_id, "sticker": file_id})

def reshape_text(text):
    """اصلاح متن فارسی/عربی با کتابخانه‌های arabic_reshaper و bidi"""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as e:
        logger.error(f"Error reshaping text: {e}")
        return text

def detect_language(text):
    """تشخیص زبان متن"""
    # الگوی فارسی/عربی
    persian_arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    persian_arabic_chars = len(persian_arabic_pattern.findall(text))
    
    # الگوی انگلیسی
    english_pattern = re.compile(r'[a-zA-Z]')
    english_chars = len(english_pattern.findall(text))
    
    if persian_arabic_chars > english_chars:
        return "persian_arabic"
    elif english_chars > 0:
        return "english"
    else:
        return "other"

def get_font(size, language="english"):
    """بارگذاری فونت بر اساس زبان"""
    if language == "persian_arabic":
        # فونت‌های فارسی/عربی
        font_paths = [
            "Vazirmatn-Regular.ttf",
            "IRANSans.ttf",
            "Vazir.ttf",
            "Vazir-Regular.ttf",
            "Sahel.ttf",
            "Samim.ttf",
            "Tanha.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
    else:
        # فونت‌های انگلیسی
        font_paths = [
            "arial.ttf",
            "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/Windows/Fonts/arial.ttf",
            "NotoSans-Regular.ttf"
        ]
    
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, size)
            logger.info(f"Successfully loaded font: {font_path} with size: {size} for {language}")
            return font
        except (OSError, IOError):
            continue
    
    try:
        return ImageFont.load_default()
    except:
        return None

def make_text_sticker(text, path, background_file_id=None):
    try:
        logger.info(f"Creating sticker with text: {text}")
        
        # تشخیص زبان
        language = detect_language(text)
        logger.info(f"Detected language: {language}")
        
        # اصلاح متن فارسی/عربی
        if language == "persian_arabic":
            text = reshape_text(text)
        
        # 🔥 بدون زوم برای فارسی، با زوم برای انگلیسی
        if language == "persian_arabic":
            # فارسی: بدون زوم، مستقیم 512×512
            img_size = 512
            img = Image.new("RGBA", (img_size, img_size), (255, 255, 255, 0))
        else:
            # انگلیسی: با زوم 2x
            img_size = 256
            img = Image.new("RGBA", (img_size, img_size), (255, 255, 255, 0))

        # 📌 اگر بکگراند هست → جایگزین کن
        if background_file_id:
            try:
                file_info = requests.get(API + f"getFile?file_id={background_file_id}").json()
                if file_info.get("ok"):
                    file_path = file_info["result"]["file_path"]
                    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                    resp = requests.get(file_url)
                    if resp.status_code == 200:
                        bg = Image.open(BytesIO(resp.content)).convert("RGBA")
                        bg = bg.resize((img_size, img_size))
                        img.paste(bg, (0, 0))
                        logger.info("Background image loaded successfully")
            except Exception as e:
                logger.error(f"Error loading background: {e}")

        draw = ImageDraw.Draw(img)
        
        # 📌 سایز فونت بر اساس زبان و اندازه تصویر
        if language == "persian_arabic":
            initial_font_size = 1200  # فارسی: سایز بزرگ برای 512×512
            max_width = 460
            max_height = 460
            min_font_size = 300
        else:
            initial_font_size = 600   # انگلیسی: سایز کوچک برای 256×256 (که بعداً زوم می‌شود)
            max_width = 230
            max_height = 230
            min_font_size = 150
            
        font = get_font(initial_font_size, language)
        
        if font is None:
            logger.error("No font could be loaded, using basic text rendering")
            font = ImageFont.load_default()

        # محاسبه اندازه متن
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except:
            try:
                w, h = draw.textsize(text, font=font)
            except:
                w, h = len(text) * (initial_font_size // 20), initial_font_size // 2

        # تنظیم خودکار سایز فونت
        font_size = initial_font_size
        
        while (w > max_width or h > max_height) and font_size > min_font_size:
            font_size -= 5
            font = get_font(font_size, language)
            if font is None:
                font = ImageFont.load_default()
                break
            
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            except:
                try:
                    w, h = draw.textsize(text, font=font)
                except:
                    w, h = len(text) * (font_size // 20), font_size // 2
        
        # مرکز کردن متن
        x = (img_size - w) / 2
        y = (img_size - h) / 2

        # 📌 حاشیه بر اساس زبان
        if language == "persian_arabic":
            outline_thickness = 8  # فارسی: حاشیه ضخیم‌تر برای 512×512
        else:
            outline_thickness = 5  # انگلیسی: حاشیه نازک‌تر برای 256×256
        
        # ایجاد حاشیه با کیفیت بالا
        for offset in range(1, outline_thickness + 1):
            # رسم حاشیه در 8 جهت اصلی
            directions = [
                (-offset, -offset), (0, -offset), (offset, -offset),
                (-offset, 0),                     (offset, 0),
                (-offset, offset),  (0, offset),  (offset, offset)
            ]
            
            for dx, dy in directions:
                try:
                    draw.text((x + dx, y + dy), text, font=font, fill="white")
                except:
                    pass

        # متن اصلی با رنگ مشکی
        try:
            draw.text((x, y), text, fill="#000000", font=font)
        except Exception as e:
            logger.error(f"Error drawing main text: {e}")
            draw.text((x, y), text, fill="#000000")

        # 🔥 زوم فقط برای انگلیسی
        if language == "persian_arabic":
            # فارسی: بدون زوم
            final_img = img
        else:
            # انگلیسی: زوم 2x
            final_img = img.resize((512, 512), Image.LANCZOS)

        # ذخیره تصویر
        final_img.save(path, "PNG", optimize=True)
        logger.info(f"Sticker saved successfully to {path} with font size: {font_size} for {language}")
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

    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
