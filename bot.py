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
                    
                    # مهم: pack_name و background را حفظ کن تا استیکر بعدی در همان پک قرار بگیرد
                    # step همچنان "text" باقی می‌ماند تا کاربر بتواند استیکر بعدی بسازد
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

def reshape_text(text):
    """اصلاح متن فارسی/عربی با حفظ ترتیب طبیعی حروف"""
    try:
        # استفاده از arabic_reshaper برای چسباندن حروف
        reshaped = arabic_reshaper.reshape(text)
        # استفاده از bidi برای ترتیب درست
        return get_display(reshaped)
    except Exception as e:
        logger.error(f"Error reshaping text: {e}")
        return text

def sanitize_pack_name(text):
    """تبدیل نام پک به فرمت قابل قبول برای Telegram API"""
    import unicodedata
    
    # حذف کاراکترهای غیرمجاز و تبدیل به ASCII
    sanitized = ""
    for char in text:
        # اگر کاراکتر ASCII حرف یا عدد باشد
        if char.isalnum() and ord(char) < 128:
            sanitized += char
        # اگر فاصله باشد
        elif char.isspace():
            sanitized += "_"
        # اگر کاراکتر فارسی باشد، به انگلیسی تبدیل کن
        elif '\u0600' <= char <= '\u06FF':  # محدوده کاراکترهای فارسی/عربی
            # تبدیل ساده فارسی به انگلیسی (می‌تونید کامل‌تر کنید)
            persian_to_english = {
                'ا': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's', 'ج': 'j', 'چ': 'ch',
                'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z', 'ر': 'r', 'ز': 'z', 'ژ': 'zh',
                'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a',
                'غ': 'gh', 'ف': 'f', 'ق': 'gh', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm',
                'ن': 'n', 'و': 'v', 'ه': 'h', 'ی': 'y', 'ئ': 'e', 'ء': 'a'
            }
            sanitized += persian_to_english.get(char, 'x')
        # اگر ایموجی باشد، حذف کن (ایموجی‌ها معمولاً در محدوده 0x1F600-0x1F64F و سایر محدوده‌ها هستند)
        elif (ord(char) >= 0x1F600 and ord(char) <= 0x1F64F) or \
             (ord(char) >= 0x1F300 and ord(char) <= 0x1F5FF) or \
             (ord(char) >= 0x1F680 and ord(char) <= 0x1F6FF) or \
             (ord(char) >= 0x1F1E0 and ord(char) <= 0x1F1FF) or \
             (ord(char) >= 0x2600 and ord(char) <= 0x26FF) or \
             (ord(char) >= 0x2700 and ord(char) <= 0x27BF) or \
             (ord(char) >= 0xFE00 and ord(char) <= 0xFE0F) or \
             (ord(char) >= 0x1F900 and ord(char) <= 0x1F9FF) or \
             (ord(char) >= 0x1F018 and ord(char) <= 0x1F270):
            # ایموجی رو حذف کن (هیچ کاراکتری اضافه نکن)
            continue
        # سایر کاراکترها رو حذف کن
        else:
            sanitized += "x"
    
    # حذف کاراکترهای تکراری _ و محدود کردن طول
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    
    # اگر خالی شد یا خیلی کوتاه بود
    if not sanitized or len(sanitized) < 2:
        sanitized = "pack"
    
    # محدود کردن طول به 64 کاراکتر (محدودیت Telegram)
    if len(sanitized) > 64:
        sanitized = sanitized[:64]
    
    return sanitized

def _measure_text(draw, text, font):
    """اندازه‌گیری امن متن (پهنای یک خط)"""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        try:
            w, h = draw.textsize(text, font=font)
            return w, h
        except Exception:
            return len(text) * max(font.size // 2, 1), font.size

def _hard_wrap_word(draw, word, font, max_width):
    """شکستن کلمات خیلی بلند به چند بخش که داخل max_width جا شوند"""
    parts = []
    start = 0
    n = len(word)
    if n == 0:
        return [word]
    while start < n:
        lo, hi = 1, n - start
        best = 1
        while lo <= hi:
            mid = (lo + hi) // 2
            segment = word[start:start + mid]
            w, _ = _measure_text(draw, segment, font)
            if w <= max_width:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        parts.append(word[start:start + best])
        start += best
        if best == 0:
            break
    return parts

def wrap_text_multiline(draw, text, font, max_width, is_rtl=False):
    """شکستن متن به خطوط متعدد با در نظر گرفتن فاصله‌ها و کلمات خیلی بلند.
    برای حفظ ترتیب طبیعی حروف، از روش ساده استفاده می‌کنیم.
    """
    if not text:
        return [""]
    
    # برای متن فارسی، از روش ساده‌تر استفاده می‌کنیم
    if is_rtl:
        # اگر متن کوتاه است، کل متن را در یک خط قرار بده
        w, _ = _measure_text(draw, text, font)
        if w <= max_width:
            return [text]
        
        # اگر متن طولانی است، بر اساس فاصله شکست بده
        words = text.split()
        if len(words) == 1:
            # اگر فقط یک کلمه است، آن را خرد کن
            return _hard_wrap_word(draw, text, font, max_width)
        
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            w, _ = _measure_text(draw, test_line, font)
            
            if w <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines or [""]
    
    # برای متن انگلیسی، از روش قبلی استفاده می‌کنیم
    tokens = re.split(r"(\s+)", text)
    lines = []
    current = ""
    for token in tokens:
        if token.strip() == "":
            # فضای خالی: فقط اگر چیزی در خط داریم اضافه شود
            tentative = current + token
            w, _ = _measure_text(draw, tentative, font)
            if w <= max_width:
                current = tentative
            else:
                if current:
                    lines.append(current.rstrip())
                    current = ""
            continue
        # کلمه غیرسفید
        tentative = current + token
        w, _ = _measure_text(draw, tentative, font)
        if w <= max_width:
            current = tentative
        else:
            # اگر خود کلمه جا نشود باید کلمه را خرد کنیم
            if current:
                lines.append(current.rstrip())
                current = ""
            # خرد کردن کلمه طولانی
            for part in _hard_wrap_word(draw, token, font, max_width):
                w_part, _ = _measure_text(draw, part, font)
                if current == "" and w_part <= max_width:
                    current = part
                else:
                    if current:
                        lines.append(current.rstrip())
                    current = part
    if current:
        lines.append(current.rstrip())
    
    return lines or [""]

def measure_multiline_block(draw, lines, font, line_spacing_px):
    """محاسبه اندازه بلوک چندخطی"""
    max_w = 0
    total_h = 0
    for i, line in enumerate(lines):
        w, h = _measure_text(draw, line, font)
        max_w = max(max_w, w)
        total_h += h
        if i < len(lines) - 1:
            total_h += line_spacing_px
    return max_w, total_h

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
            "NotoSansArabic-Regular.ttf",
            "NotoNaskhArabic-Regular.ttf",
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
        
        # 🔥 رندر روی 256×256 و در پایان زوم 2x برای هر دو زبان
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
        
        # 📌 تنظیمات فونت و باکس متن (بهینه‌سازی برای متن فارسی)
        if language == "persian_arabic":
            initial_font_size = 80   # کاهش بیشتر برای فارسی
            min_font_size = 20       # کاهش بیشتر برای فارسی
        else:
            initial_font_size = 220  # افزایش فونت انگلیسی
            min_font_size = 60       # افزایش حداقل فونت انگلیسی
        max_width = 140              # کاهش بیشتر برای فارسی
        max_height = 140             # کاهش بیشتر برای فارسی
            
        font = get_font(initial_font_size, language)
        
        if font is None:
            logger.error("No font could be loaded, using basic text rendering")
            font = ImageFont.load_default()

        # محاسبه اندازه متن اولیه برای تنظیم فونت
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
        
        while True:
            # بازشکستن با فونت جاری و اندازه‌گیری بلوک چندخطی
            line_spacing = max(int(font_size * 0.15), 4)
            wrapped_lines = wrap_text_multiline(draw, text, font, max_width, is_rtl=(language=="persian_arabic"))
            block_w, block_h = measure_multiline_block(draw, wrapped_lines, font, line_spacing)
            if (block_w <= max_width and block_h <= max_height):
                lines = wrapped_lines
                break
            if font_size <= min_font_size:
                # حداقل ممکن؛ جلوگیری از حلقه بی‌نهایت
                lines = wrapped_lines
                break
            font_size -= 3  # کاهش کمتر برای تنظیم دقیق‌تر
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
        
        # شکستن متن به چند خط در محدوده
        if language == "persian_arabic":
            line_spacing = max(int(font_size * 0.05), 1)  # فاصله خیلی کم برای فارسی
        else:
            line_spacing = max(int(font_size * 0.15), 3)  # فاصله متوسط برای انگلیسی
        lines = wrap_text_multiline(draw, text, font, max_width, is_rtl=(language=="persian_arabic"))
        block_w, block_h = measure_multiline_block(draw, lines, font, line_spacing)
        x = (img_size - block_w) / 2
        # وسط‌چین عمودی برای هر دو زبان
        is_rtl = (language == "persian_arabic")
        y = (img_size - block_h) / 2

        # 📌 حاشیه بر اساس زبان (کاهش برای متن کوچک‌تر)
        if language == "persian_arabic":
            outline_thickness = 2  # فارسی: حاشیه نازک
        else:
            outline_thickness = 1  # انگلیسی: حاشیه خیلی نازک
        
        # رسم هر خط با حاشیه و متن
        current_y = y
        for line in lines:
            w_line, h_line = _measure_text(draw, line, font)
            # وسط‌چین برای هر دو زبان
            line_x = x + (block_w - w_line) / 2
            # حاشیه
            for offset in range(1, outline_thickness + 1):
                directions = [
                    (-offset, -offset), (0, -offset), (offset, -offset),
                    (-offset, 0),                     (offset, 0),
                    (-offset, offset),  (0, offset),  (offset, offset)
                ]
                for dx, dy in directions:
                    try:
                        draw.text((line_x + dx, current_y + dy), line, font=font, fill="white")
                    except Exception:
                        pass
            # متن اصلی
            try:
                draw.text((line_x, current_y), line, fill="#000000", font=font)
            except Exception as e:
                logger.error(f"Error drawing line: {e}")
                draw.text((line_x, current_y), line, fill="#000000")
            current_y += h_line + line_spacing

        # 🔥 زوم کمتر برای متن فارسی جهت جلوگیری از خروج از کادر
        if language == "persian_arabic":
            final_img = img.resize((400, 400), Image.LANCZOS)  # زوم کمتر برای فارسی
        else:
            final_img = img.resize((512, 512), Image.LANCZOS)  # زوم عادی برای انگلیسی

        # ذخیره تصویر با بهینه‌سازی برای استیکر
        final_img.save(path, "PNG", optimize=True, compress_level=9)
        
        # بررسی حجم فایل
        file_size = os.path.getsize(path)
        if file_size > 512 * 1024:  # اگر بیشتر از 512KB باشد
            logger.warning(f"Sticker file too large: {file_size} bytes, compressing...")
            # کاهش کیفیت
            final_img.save(path, "PNG", optimize=True, compress_level=9, quality=85)
        
        logger.info(f"Sticker saved successfully to {path} with font size: {font_size} for {language}, size: {os.path.getsize(path)} bytes")
        return True
        
    except Exception as e:
        logger.error(f"make_text_sticker error: {e}")
        return False

def show_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🎁 تست رایگان", "⭐ اشتراک"],
            ["ℹ️ درباره", "📞 پشتیبانی"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "👋 خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:",
        "reply_markup": keyboard
    })

def check_sticker_limit(chat_id):
    """بررسی محدودیت استیکر برای کاربر"""
    if chat_id not in user_data:
        return 5, time.time() + 24 * 3600  # 5 استیکر، 24 ساعت بعد
    
    current_time = time.time()
    user_info = user_data[chat_id]
    
    # دریافت زمان آخرین reset (اگر وجود نداشت، از الان شروع کن)
    last_reset = user_info.get("last_reset", current_time)
    
    # محاسبه زمان reset بعدی (بر اساس آخرین reset)
    next_reset = last_reset + 24 * 3600
    
    # اگر زمان reset گذشته، reset کن
    if current_time >= next_reset:
        user_info["sticker_usage"] = []
        user_info["last_reset"] = current_time
        next_reset = current_time + 24 * 3600
        save_user_data()  # ذخیره تغییرات
        logger.info(f"Reset limit for user {chat_id} at {current_time}")
    
    # شمارش استیکرهای استفاده شده در 24 ساعت گذشته
    used_stickers = len(user_info.get("sticker_usage", []))
    remaining = 5 - used_stickers
    
    return max(0, remaining), next_reset

def record_sticker_usage(chat_id):
    """ثبت استفاده از استیکر"""
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
    
    current_time = time.time()
    user_info = user_data[chat_id]
    
    # دریافت زمان آخرین reset (اگر وجود نداشت، از الان شروع کن)
    last_reset = user_info.get("last_reset", current_time)
    
    # محاسبه زمان reset بعدی
    next_reset = last_reset + 24 * 3600
    
    # اگر زمان reset گذشته، reset کن
    if current_time >= next_reset:
        user_info["sticker_usage"] = []
        user_info["last_reset"] = current_time
        logger.info(f"Reset limit for user {chat_id} at {current_time}")
    
    # اضافه کردن زمان استفاده
    user_info["sticker_usage"].append(current_time)
    save_user_data()  # ذخیره فوری

def get_user_packs_from_api(chat_id):
    """دریافت پک‌های کاربر از API تلگرام"""
    try:
        # دریافت اطلاعات کاربر
        user_info = requests.get(API + f"getChat?chat_id={chat_id}").json()
        first_name = user_info.get("result", {}).get("first_name", "User")
        
        # جستجو برای پک‌هایی که با نام کاربر شروع می‌شوند
        # این روش کامل نیست اما می‌تواند کمک کند
        packs = []
        
        # اگر pack_name فعلی وجود دارد، آن را بررسی کن
        current_pack = user_data.get(chat_id, {}).get("pack_name")
        if current_pack:
            resp = requests.get(API + f"getStickerSet?name={current_pack}").json()
            if resp.get("ok"):
                packs.append({
                    "name": current_pack,
                    "title": f"{first_name}'s Stickers"
                })
        
        return packs
    except Exception as e:
        logger.error(f"Error getting user packs from API: {e}")
        return []

def check_channel_membership(chat_id):
    """بررسی عضویت کاربر در کانال اجباری"""
    try:
        # استخراج channel_id از لینک
        if CHANNEL_LINK.startswith("@"):
            channel_username = CHANNEL_LINK[1:]  # حذف @
        elif "t.me/" in CHANNEL_LINK:
            channel_username = CHANNEL_LINK.split("t.me/")[-1]
            if channel_username.startswith("@"):
                channel_username = channel_username[1:]
        else:
            channel_username = CHANNEL_LINK
        
        # بررسی عضویت
        response = requests.get(API + f"getChatMember", params={
            "chat_id": f"@{channel_username}",
            "user_id": chat_id
        }).json()
        
        if response.get("ok"):
            status = response["result"]["status"]
            # اگر عضو است (member, administrator, creator)
            return status in ["member", "administrator", "creator"]
        else:
            logger.error(f"Error checking membership: {response}")
            return False
            
    except Exception as e:
        logger.error(f"Error in check_channel_membership: {e}")
        return False

def send_membership_required_message(chat_id):
    """ارسال پیام عضویت اجباری"""
    message = f"""🔒 عضویت در کانال اجباری است!

برای استفاده از ربات، ابتدا باید عضو کانال ما شوید:

📢 {CHANNEL_LINK}

بعد از عضویت، دوباره /start را بزنید."""
    
    # ایجاد دکمه عضویت
    keyboard = {
        "inline_keyboard": [[
            {
                "text": "📢 عضویت در کانال",
                "url": f"https://t.me/{CHANNEL_LINK.replace('@', '')}"
            }
        ]]
    }
    
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": message,
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
