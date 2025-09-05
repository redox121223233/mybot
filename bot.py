import os
import logging
import re
import time
import json
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
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "@YourChannel")  # لینک کانال اجباری
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# دیتابیس ساده در حافظه
user_data = {}

# فایل ذخیره‌سازی داده‌ها
DATA_FILE = "user_data.json"

def load_user_data():
    """بارگذاری داده‌های کاربر از فایل"""
    global user_data
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
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            
            # اگر کاربر قبلاً وجود دارد، داده‌های مهم را حفظ کن
            if chat_id in user_data:
                old_data = user_data[chat_id]
                user_data[chat_id] = {
                    "mode": None, 
                    "count": 0, 
                    "step": None, 
                    "pack_name": None, 
                    "background": None, 
                    "created_packs": [],
                    "sticker_usage": old_data.get("sticker_usage", []),  # حفظ محدودیت
                    "last_reset": old_data.get("last_reset", time.time())  # حفظ زمان reset
                }
            else:
                user_data[chat_id] = {
                    "mode": None, 
                    "count": 0, 
                    "step": None, 
                    "pack_name": None, 
                    "background": None, 
                    "created_packs": [],
                    "sticker_usage": [],
                    "last_reset": time.time()
                }
            show_main_menu(chat_id)
            return "ok"

        if text == "🎁 تست رایگان":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
                
            if chat_id not in user_data:
                user_data[chat_id] = {
                    "mode": None, 
                    "count": 0, 
                    "step": None, 
                    "pack_name": None, 
                    "background": None, 
                    "created_packs": [],
                    "sticker_usage": [],
                    "last_reset": time.time()
                }
            else:
                # اگر کاربر قبلاً وجود دارد، created_packs را حفظ کن
                if "created_packs" not in user_data[chat_id]:
                    user_data[chat_id]["created_packs"] = []
                if "sticker_usage" not in user_data[chat_id]:
                    user_data[chat_id]["sticker_usage"] = []
                if "last_reset" not in user_data[chat_id]:
                    user_data[chat_id]["last_reset"] = time.time()
            
            # بررسی محدودیت استیکر
            remaining, next_reset = check_sticker_limit(chat_id)
            if remaining <= 0:
                next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                send_message(chat_id, f"⏰ محدودیت روزانه شما تمام شده!\n\n🔄 زمان بعدی: {next_reset_time}\n\n💎 برای ساخت استیکر نامحدود، اشتراک تهیه کنید.")
                return "ok"
            
            user_data[chat_id]["mode"] = "free"
            # مهم: count, pack_name و background را reset نکن اگر کاربر قبلاً پکی دارد
            if not user_data[chat_id].get("pack_name"):
                user_data[chat_id]["count"] = 0
                user_data[chat_id]["step"] = "ask_pack_choice"
                user_data[chat_id]["pack_name"] = None
                user_data[chat_id]["background"] = None
            else:
                # اگر کاربر قبلاً پکی دارد، مستقیماً به مرحله text برو
                user_data[chat_id]["step"] = "text"
            
            # نمایش وضعیت محدودیت
            next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
            limit_info = f"📊 وضعیت شما: {remaining}/5 استیکر باقی مانده\n🔄 زمان بعدی: {next_reset_time}\n\n"
            
            # بررسی پک‌های موجود
            created_packs = user_data[chat_id].get("created_packs", [])
            if user_data[chat_id].get("pack_name"):
                # اگر کاربر قبلاً پکی دارد، مستقیماً به ساخت استیکر ادامه دهد
                pack_name = user_data[chat_id]["pack_name"]
                send_message(chat_id, limit_info + f"✅ ادامه ساخت استیکر در پک فعلی\n✍️ متن استیکر بعدی را بفرست:\n\n📷 یا عکس جدید برای تغییر بکگراند بفرست:")
            elif created_packs:
                send_message(chat_id, limit_info + "📝 آیا می‌خواهید پک جدید بسازید یا به پک قبلی اضافه کنید؟\n1. ساخت پک جدید\n2. اضافه کردن به پک قبلی")
            else:
                send_message(chat_id, limit_info + "📝 شما هنوز پکی ندارید. لطفاً یک نام برای پک استیکر خود انتخاب کن:\n\n💡 می‌تونید فارسی، انگلیسی یا حتی ایموجی بنویسید، ربات خودش تبدیلش می‌کنه!")
                user_data[chat_id]["step"] = "pack_name"
            return "ok"

        state = user_data.get(chat_id, {})
        if state.get("mode") == "free":
            step = state.get("step")

            if step == "ask_pack_choice":
                if text == "1":  # ساخت پک جدید
                    send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:\n\n💡 می‌تونید فارسی، انگلیسی یا حتی ایموجی بنویسید، ربات خودش تبدیلش می‌کنه!")
                    user_data[chat_id]["step"] = "pack_name"
                elif text == "2":  # اضافه کردن به پک قبلی
                    created_packs = user_data[chat_id].get("created_packs", [])
                    if created_packs:
                        # نمایش لیست پک‌های موجود
                        pack_list = ""
                        for i, pack in enumerate(created_packs, 1):
                            pack_list += f"{i}. {pack['title']}\n"
                        send_message(chat_id, f"📂 پک‌های موجود شما:\n{pack_list}\nلطفاً شماره پک مورد نظر را انتخاب کنید:")
                        user_data[chat_id]["step"] = "select_pack"
                    else:
                        send_message(chat_id, "❌ هنوز پک استیکری نداری. اول باید پک جدید بسازی.")
                        user_data[chat_id]["step"] = "pack_name"
                        send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:\n\n💡 می‌تونید فارسی، انگلیسی یا حتی ایموجی بنویسید، ربات خودش تبدیلش می‌کنه!")
                return "ok"

    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
                logger.info(f"Loaded user data: {len(user_data)} users")
        else:
            user_data = {}
    except Exception as e:
        logger.error(f"Error loading user data: {e}")
        user_data = {}

def save_user_data():
    """ذخیره داده‌های کاربر در فایل"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved user data: {len(user_data)} users")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

# بارگذاری داده‌ها در شروع
load_user_data()

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is running!"

# ------------ ادامه (webhook و ...) در بخش بعدی -------------
            if step == "select_pack":
                try:
                    pack_index = int(text) - 1
                    created_packs = user_data[chat_id].get("created_packs", [])
                    if 0 <= pack_index < len(created_packs):
                        selected_pack = created_packs[pack_index]
                        user_data[chat_id]["pack_name"] = selected_pack["name"]
                        send_message(chat_id, f"✅ پک '{selected_pack['title']}' انتخاب شد.\n📷 یک عکس برای بکگراند استیکرت بفرست:")
                        user_data[chat_id]["step"] = "background"
                    else:
                        send_message(chat_id, "❌ شماره پک نامعتبر است. لطفاً دوباره انتخاب کنید:")
                except ValueError:
                    send_message(chat_id, "❌ لطفاً یک شماره معتبر وارد کنید:")
                return "ok"

            if step == "pack_name":
                # تبدیل نام پک به فرمت قابل قبول
                original_name = text
                pack_name = sanitize_pack_name(text)
                full_pack_name = f"{pack_name}_by_{BOT_USERNAME}"
                
                # اگر نام تبدیل شده با نام اصلی متفاوت بود، به کاربر اطلاع بده
                if pack_name != original_name.replace(" ", "_"):
                    send_message(chat_id, f"ℹ️ نام پک شما از '{original_name}' به '{pack_name}' تبدیل شد تا با قوانین تلگرام سازگار باشد.")
                
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
                # بررسی محدودیت قبل از ساخت استیکر
                remaining, next_reset = check_sticker_limit(chat_id)
                if remaining <= 0:
                    next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                    send_message(chat_id, f"⏰ محدودیت روزانه شما تمام شده!\n\n🔄 زمان بعدی: {next_reset_time}\n\n💎 برای ساخت استیکر نامحدود، اشتراک تهیه کنید.")
                    return "ok"
                
                text_sticker = text
                send_message(chat_id, "⚙️ در حال ساخت استیکر...")
                background_file_id = user_data[chat_id].get("background")
                
                # Debug: بررسی pack_name
                pack_name = user_data[chat_id].get("pack_name")
                logger.info(f"Creating sticker for pack: {pack_name}")
                
                # ارسال استیکر و بررسی موفقیت
                success = send_as_sticker(chat_id, text_sticker, background_file_id)
                
                if success:
                    user_data[chat_id]["count"] += 1
                    record_sticker_usage(chat_id)  # ثبت استفاده
                    
                    # نمایش وضعیت محدودیت
                    remaining, next_reset = check_sticker_limit(chat_id)
                    next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                    limit_info = f"\n📊 وضعیت: {remaining}/5 استیکر باقی مانده\n🔄 زمان بعدی: {next_reset_time}"
                    
                    send_message(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد.{limit_info}\n\n✍️ متن استیکر بعدی را بفرست:\n\n📷 یا عکس جدید برای تغییر بکگراند بفرست:")
                    
                return "ok"

        # دکمه‌های منو
        if text == "⭐ اشتراک":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            send_message(chat_id, "💳 بخش اشتراک بعداً فعال خواهد شد.")
        elif text == "ℹ️ درباره":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            send_message(chat_id, "ℹ️ این ربات برای ساخت استیکر متنی است. نسخه فعلی رایگان است.")
        elif text == "📞 پشتیبانی":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            support_id = os.environ.get("SUPPORT_ID", "@YourSupportID")
            send_message(chat_id, f"📞 برای پشتیبانی با {support_id} در تماس باش.")

    # 📌 پردازش عکس
    elif "photo" in msg:
        state = user_data.get(chat_id, {})
        if state.get("mode") == "free":
            photos = msg.get("photo", [])
            if photos:
                file_id = photos[-1].get("file_id")
                if file_id:
                    if state.get("step") == "background":
                        # عکس اول برای بکگراند
                        user_data[chat_id]["background"] = file_id
                        user_data[chat_id]["step"] = "text"
                        send_message(chat_id, "✍️ حالا متن استیکرت رو بفرست:")
                    elif state.get("step") == "text":
                        # تغییر بکگراند در حین ساخت استیکر
                        user_data[chat_id]["background"] = file_id
                        send_message(chat_id, "✅ بکگراند تغییر کرد!\n✍️ متن استیکر بعدی را بفرست:")

    return "ok"
def send_as_sticker(chat_id, text, background_file_id=None):
    sticker_path = "sticker.png"
    ok = make_text_sticker(text, sticker_path, background_file_id)
    if not ok:
        send_message(chat_id, "❌ خطا در ساخت استیکر")
        return False

    pack_name = user_data[chat_id].get("pack_name")
    if not pack_name:
        send_message(chat_id, "❌ خطا: نام پک تعریف نشده")
        return False
        
    # دریافت نام کاربر
    user_info = requests.get(API + f"getChat?chat_id={chat_id}").json()
    username = user_info.get("result", {}).get("username", f"user_{chat_id}")
    first_name = user_info.get("result", {}).get("first_name", "User")

    pack_title = f"{first_name}'s Stickers"

    resp = requests.get(API + f"getStickerSet?name={pack_name}").json()
    sticker_created = False

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
            if r.json().get("ok"):
                sticker_created = True
                # ذخیره پک جدید در لیست
                if "created_packs" not in user_data[chat_id]:
                    user_data[chat_id]["created_packs"] = []
                
                # بررسی اینکه پک قبلاً در لیست نیست
                pack_exists = False
                for existing_pack in user_data[chat_id]["created_packs"]:
                    if existing_pack["name"] == pack_name:
                        pack_exists = True
                        break

                if not pack_exists:
                    user_data[chat_id]["created_packs"].append({
                        "name": pack_name,
                        "title": pack_title
                    })
                    logger.info(f"Pack added to created_packs: {pack_name} - {pack_title}")
                    logger.info(f"User {chat_id} created_packs: {user_data[chat_id]['created_packs']}")
                    save_user_data()  # ذخیره فوری
            else:
                send_message(chat_id, f"❌ خطا در ساخت پک: {r.json().get('description', 'خطای نامشخص')}")
                return False
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
            if r.json().get("ok"):
                sticker_created = True
            else:
                send_message(chat_id, f"❌ خطا در اضافه کردن استیکر: {r.json().get('description', 'خطای نامشخص')}")
                return False

    # ارسال استیکر به کاربر - ارسال از پک (تنها روش صحیح)
    if sticker_created:
        try:
            # کمی صبر کنیم تا API پک را به‌روزرسانی کند
            time.sleep(1)
            
            # دریافت پک و ارسال آخرین استیکر
            final = requests.get(API + f"getStickerSet?name={pack_name}").json()
            if final.get("ok"):
                stickers = final["result"]["stickers"]
                if stickers:
                    file_id = stickers[-1]["file_id"]
                    send_resp = requests.post(API + "sendSticker", data={"chat_id": chat_id, "sticker": file_id})
                    logger.info(f"Send sticker resp: {send_resp.json()}")
                    
                    if send_resp.json().get("ok"):
                        return True
                    else:
                        logger.error(f"Failed to send sticker: {send_resp.json()}")
                        send_message(chat_id, "❌ خطا در ارسال استیکر")
                        return False
                else:
                    send_message(chat_id, "❌ استیکر در پک پیدا نشد")
                    return False
            else:
                send_message(chat_id, "❌ پک پیدا نشد")
                return False
        except Exception as e:
            logger.error(f"Error sending sticker: {e}")
            send_message(chat_id, "❌ خطا در ارسال استیکر")
            return False
    return False
def get_font(size, language="english"):
    # فونت مناسب فارسی یا انگلیسی از پوشه پروژه یا مسیرهای رایج
    if language == "persian_arabic":
        font_options = [
            "Vazirmatn-Regular.ttf", "Vazir-Regular.ttf", "IRANSans.ttf", 
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
    else:
        font_options = [
            "arial.ttf", "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
    for font_path in font_options:
        try:
            font = ImageFont.truetype(font_path, size)
            logger.info(f"Font loaded: {font_path}")
            return font
        except Exception as e:
            logger.warning(f"Font load failed ({font_path}): {e}")
    logger.warning("No proper font found! Using default font (may break RTL letters!)")
    return ImageFont.load_default()

def reshape_text(text):
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as e:
        logger.error(f"Error reshaping text: {e}")
        return text

def make_text_sticker(text, path, background_file_id=None):
    try:
        logger.info(f"Creating sticker for text: {text}")
        language = detect_language(text)
        is_rtl = language == "persian_arabic"
        text_display = reshape_text(text) if is_rtl else text

        img_size = 256
        img = Image.new("RGBA", (img_size, img_size), (255,255,255,0))
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
                        img.paste(bg, (0,0))
                        logger.info("BG OK")
            except Exception as e:
                logger.error(f"BG load error: {e}")

        draw = ImageDraw.Draw(img)
        min_font_size = 42
        max_font_size = 170 if language == "english" else 200
        font_size = max_font_size
        block_w = block_h = 99999
        while (block_w > 200 or block_h > 200) and font_size >= min_font_size:
            font = get_font(font_size, language)
            lines = wrap_text_multiline(draw, text_display, font, 200, is_rtl)
            block_w, block_h = measure_multiline_block(draw, lines, font, int(font_size * 0.14))
            if block_w > 200 or block_h > 200:
                font_size -= 6

        x = (img_size - block_w) // 2
        y = (img_size - block_h) // 2
        line_spacing = max(int(font_size * 0.14), 3)
        current_y = y
        for line in lines:
            w, h = _measure_text(draw, line, font)
            line_x = x + (block_w - w) if is_rtl else x + (block_w - w)//2
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    if dx!=0 or dy!=0:
                        draw.text((line_x+dx, current_y+dy), line, font=font, fill="white")
            draw.text((line_x, current_y), line, font=font, fill="black")
            current_y += h + line_spacing
        img2 = img.resize((512,512), Image.LANCZOS)
        img2.save(path, "PNG", optimize=True)
        return True
    except Exception as e:
        logger.error(f"Sticker error: {e}")
        return False
# ... sanitize_pack_name، wrap_text_multiline، measure_multiline_block،
# detect_language، _measure_text، _hard_wrap_word و...

# (بقیه کد دقیقا مطابق کد اولیه خودت کپی کن)

if __name__ == "__main__":
    # تست مخصوص فونت و reshape
    imgtest = Image.new("RGBA", (400, 100), (255,255,255,0))
    d = ImageDraw.Draw(imgtest)
    fnt = get_font(48, "persian_arabic")
    sample_txt = reshape_text("سلام دوست من! خوش آمدید 🍐")
    d.text((10,25), sample_txt, font=fnt, fill="black")
    imgtest.save("test_reshaped_fa.png")

    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        resp = requests.get(API + f"setWebhook?url={webhook_url}")
        logger.info(f"setWebhook: {resp.json()}")
    else:
        logger.warning("⚠️ APP_URL is not set. Webhook not registered.")

    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)

