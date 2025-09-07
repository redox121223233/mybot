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

# --- Simple i18n ---
LOCALES = {
    "fa": {
        "main_menu": "👋 خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:",
        "lang_set_fa": "✅ زبان به فارسی تغییر کرد.",
        "lang_set_en": "✅ Language set to English.",
        "choose_lang": "🌍 انتخاب زبان:\n\nانتخاب کنید:",
    },
    "en": {
        "main_menu": "👋 Welcome! Choose an option:",
        "lang_set_fa": "✅ زبان به فارسی تغییر کرد.",
        "lang_set_en": "✅ Language set to English.",
        "choose_lang": "🌍 Choose language:\n\nSelect:",
    }
}

def load_locales():
    """Optionally override LOCALES with files in locales/*.json"""
    try:
        import glob
        for path in glob.glob(os.path.join("locales", "*.json")):
            try:
                code = os.path.splitext(os.path.basename(path))[0]
                with open(path, "r", encoding="utf-8") as f:
                    LOCALES[code] = json.load(f)
                logger.info(f"Loaded locale: {code} from {path}")
            except Exception as e:
                logger.error(f"Failed to load locale {path}: {e}")
        # همچنین فایل‌های تخت در ریشه پروژه را بارگذاری کن
        flat_files = {
            "fa": "localesfa.json",
            "en": "localesen.json"
        }
        for code, fname in flat_files.items():
            try:
                if os.path.exists(fname):
                    with open(fname, "r", encoding="utf-8") as f:
                        LOCALES[code] = json.load(f)
                    logger.info(f"Loaded flat locale: {code} from {fname}")
            except Exception as e:
                logger.error(f"Failed to load flat locale {fname}: {e}")
    except Exception as e:
        logger.error(f"Error scanning locales: {e}")

def get_lang(chat_id):
    return user_data.get(chat_id, {}).get("lang", "fa")

def tr(chat_id, key, fallback_text):
    lang = get_lang(chat_id)
    return LOCALES.get(lang, {}).get(key, fallback_text)

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

        # ابتدا دستورات خاص را بررسی کن (قبل از پردازش حالت)
        if text == "/start":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            
            # همیشه به منوی اصلی برگرد (حتی اگر در حال ساخت استیکر هستید)
            if chat_id in user_data:
                old_data = user_data[chat_id]
                user_data[chat_id] = {
                    "mode": None, 
                    "count": 0, 
                    "step": None, 
                    "pack_name": None, 
                    "background": None, 
                    "created_packs": old_data.get("created_packs", []),  # حفظ پک‌های ساخته شده
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

        # دکمه بازگشت - همیشه به منوی اصلی برگرد و reset کن
        if text == "🔙 بازگشت":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            
            # همیشه reset کن (جز محدودیت و پک‌های ساخته شده)
            if chat_id in user_data:
                old_data = user_data[chat_id]
                user_data[chat_id] = {
                    "mode": None, 
                    "count": 0, 
                    "step": None, 
                    "pack_name": None, 
                    "background": None, 
                    "created_packs": old_data.get("created_packs", []),  # حفظ پک‌های ساخته شده
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

        # پردازش دکمه‌های اصلی (قبل از پردازش حالت‌ها)
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
                send_message_with_back_button(chat_id, limit_info + f"✅ ادامه ساخت استیکر در پک فعلی\n✍️ متن استیکر بعدی را بفرست:\n\n📷 یا عکس جدید برای تغییر بکگراند بفرست:")
            elif created_packs:
                send_message(chat_id, limit_info + "📝 آیا می‌خواهید پک جدید بسازید یا به پک قبلی اضافه کنید؟\n1. ساخت پک جدید\n2. اضافه کردن به پک قبلی")
            else:
                send_message(chat_id, limit_info + "📝 شما هنوز پکی ندارید. لطفاً یک نام برای پک استیکر خود انتخاب کن:\n\n💡 می‌تونید فارسی، انگلیسی یا حتی ایموجی بنویسید، ربات خودش تبدیلش می‌کنه!")
                user_data[chat_id]["step"] = "pack_name"
            return "ok"

        # پردازش دکمه‌های طراحی پیشرفته
        if text == "🎨 انتخاب رنگ متن":
            # تنظیم حالت طراحی پیشرفته
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["mode"] = "advanced_design"
            user_data[chat_id]["step"] = "color_selection"
            show_color_menu(chat_id)
            return "ok"
        elif text == "📝 انتخاب فونت":
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["mode"] = "advanced_design"
            user_data[chat_id]["step"] = "font_selection"
            show_font_menu(chat_id)
            return "ok"
        elif text == "📏 اندازه متن":
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["mode"] = "advanced_design"
            user_data[chat_id]["step"] = "size_selection"
            show_size_menu(chat_id)
            return "ok"
        elif text == "📍 موقعیت متن":
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["mode"] = "advanced_design"
            user_data[chat_id]["step"] = "position_selection"
            show_position_menu(chat_id)
            return "ok"
        elif text == "🖼️ رنگ پس‌زمینه":
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["mode"] = "advanced_design"
            user_data[chat_id]["step"] = "background_color_selection"
            show_background_color_menu(chat_id)
            return "ok"
        elif text == "✨ افکت‌های ویژه":
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["mode"] = "advanced_design"
            user_data[chat_id]["step"] = "effect_selection"
            show_effects_menu(chat_id)
            return "ok"

        # پردازش دکمه‌های رنگ
        if text in ["🔴 قرمز", "🔵 آبی", "🟢 سبز", "🟡 زرد", "🟣 بنفش", "🟠 نارنجی", "🩷 صورتی", "⚫ مشکی", "⚪ سفید", "🔘 خاکستری"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["text_color"] = text.split(" ")[1]  # استخراج نام رنگ
            user_data[chat_id]["mode"] = "free"
            if not user_data[chat_id].get("pack_name"):
                user_data[chat_id]["step"] = "pack_name"
                send_message(chat_id, f"✅ رنگ {text.split(' ')[1]} انتخاب شد!\n\n📝 حالا یک نام برای پک استیکر خود انتخاب کن:")
            else:
                user_data[chat_id]["step"] = "text"
                send_message_with_back_button(chat_id, f"✅ رنگ {text.split(' ')[1]} انتخاب شد!\n\n✍️ حالا متن استیکرت رو بفرست:")
            return "ok"

        # پردازش دکمه‌های فونت
        if text in ["📝 فونت عادی", "📝 فونت ضخیم", "📝 فونت نازک", "📝 فونت کج", "📝 فونت فانتزی", "📝 فونت کلاسیک"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["font_style"] = text
            user_data[chat_id]["mode"] = "free"
            if not user_data[chat_id].get("pack_name"):
                user_data[chat_id]["step"] = "pack_name"
                send_message(chat_id, f"✅ {text} انتخاب شد!\n\n📝 حالا یک نام برای پک استیکر خود انتخاب کن:")
            else:
                user_data[chat_id]["step"] = "text"
                send_message_with_back_button(chat_id, f"✅ {text} انتخاب شد!\n\n✍️ حالا متن استیکرت رو بفرست:")
            return "ok"

        # پردازش دکمه‌های اندازه
        if text in ["📏 کوچک", "📏 متوسط", "📏 بزرگ", "📏 خیلی کوچک", "📏 خیلی بزرگ"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["text_size"] = text
            user_data[chat_id]["mode"] = "free"
            if not user_data[chat_id].get("pack_name"):
                user_data[chat_id]["step"] = "pack_name"
                send_message(chat_id, f"✅ اندازه {text.split(' ')[1]} انتخاب شد!\n\n📝 حالا یک نام برای پک استیکر خود انتخاب کن:")
            else:
                user_data[chat_id]["step"] = "text"
                send_message_with_back_button(chat_id, f"✅ اندازه {text.split(' ')[1]} انتخاب شد!\n\n✍️ حالا متن استیکرت رو بفرست:")
            return "ok"

        # پردازش دکمه‌های قالب‌های آماده
        if text in ["🎉 تولد", "💒 عروسی", "🎊 جشن", "💝 عاشقانه", "😄 خنده‌دار", "🔥 هیجان‌انگیز", "📚 آموزشی", "💼 کاری", "🏠 خانوادگی"]:
            apply_template(chat_id, text)
            return "ok"

        # پردازش دکمه‌های تنظیمات
        if text == "🌙 حالت تاریک":
            set_dark_mode(chat_id, True)
            return "ok"
        elif text == "🌍 زبان":
            show_language_menu(chat_id)
            return "ok"
        elif text in ["🇮🇷 فارسی", "🇺🇸 انگلیسی"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["lang"] = "fa" if "🇮🇷" in text else "en"
            save_user_data()
            msg = tr(chat_id, "lang_set_fa", "✅ زبان به فارسی تغییر کرد.") if user_data[chat_id]["lang"] == "fa" else tr(chat_id, "lang_set_en", "✅ Language set to English.")
            send_message_with_back_button(chat_id, msg)
            return "ok"
        elif text == "💾 ذخیره قالب":
            save_template(chat_id)
            return "ok"
        elif text == "📤 اشتراک‌گذاری":
            share_sticker(chat_id)
            return "ok"

        # دکمه‌های منو
        if text == "🎨 طراحی پیشرفته":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_advanced_design_menu(chat_id)
            return "ok"
        elif text == "📚 قالب‌های آماده":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_template_menu(chat_id)
            return "ok"
        elif text == "📝 تاریخچه":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_history(chat_id)
            return "ok"
        elif text == "⚙️ تنظیمات":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_settings_menu(chat_id)
            return "ok"
        elif text == "⭐ اشتراک":
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

        # پردازش حالت کاربر (بعد از دکمه‌ها)
        if process_user_state(chat_id, text):
            return "ok"

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
                        send_message_with_back_button(chat_id, "✍️ حالا متن استیکرت رو بفرست:")
                    elif state.get("step") == "text":
                        # تغییر بکگراند در حین ساخت استیکر
                        user_data[chat_id]["background"] = file_id
                        send_message_with_back_button(chat_id, "✅ بکگراند تغییر کرد!\n✍️ متن استیکر بعدی را بفرست:")

    return "ok"

def process_user_state(chat_id, text):
    """پردازش حالت کاربر - این تابع جداگانه برای پردازش حالت‌ها"""
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
            return True

        if step == "select_pack":
            try:
                pack_index = int(text) - 1
                created_packs = user_data[chat_id].get("created_packs", [])
                if 0 <= pack_index < len(created_packs):
                    selected_pack = created_packs[pack_index]
                    user_data[chat_id]["pack_name"] = selected_pack["name"]
                    send_message_with_back_button(chat_id, f"✅ پک '{selected_pack['title']}' انتخاب شد.\n📷 یک عکس برای بکگراند استیکرت بفرست:")
                    user_data[chat_id]["step"] = "background"
                else:
                    send_message(chat_id, "❌ شماره پک نامعتبر است. لطفاً دوباره انتخاب کنید:")
            except ValueError:
                send_message(chat_id, "❌ لطفاً یک شماره معتبر وارد کنید:")
            return True

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
                return True
            
            user_data[chat_id]["pack_name"] = full_pack_name
            
            # اگر کاربر از قالب استفاده کرده، مستقیماً به ساخت استیکر برو
            if user_data[chat_id].get("background_style"):
                user_data[chat_id]["step"] = "text"
                send_message_with_back_button(chat_id, "✍️ حالا متن استیکرت رو بفرست:")
            else:
                send_message_with_back_button(chat_id, "📷 یک عکس برای بکگراند استیکرت بفرست:")
                user_data[chat_id]["step"] = "background"
            return True

        if step == "background":
            # این مرحله فقط برای عکس است، متن نباید اینجا پردازش شود
            return False

        if step == "text":
            # بررسی محدودیت قبل از ساخت استیکر
            remaining, next_reset = check_sticker_limit(chat_id)
            if remaining <= 0:
                next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                send_message(chat_id, f"⏰ محدودیت روزانه شما تمام شده!\n\n🔄 زمان بعدی: {next_reset_time}\n\n💎 برای ساخت استیکر نامحدود، اشتراک تهیه کنید.")
                return True
            
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
                
                # نمایش تنظیمات فعلی
                settings_info = ""
                if user_data[chat_id].get("text_color"):
                    settings_info += f"\n🎨 رنگ: {user_data[chat_id]['text_color']}"
                if user_data[chat_id].get("font_style"):
                    settings_info += f"\n📝 فونت: {user_data[chat_id]['font_style']}"
                if user_data[chat_id].get("text_size"):
                    settings_info += f"\n📏 اندازه: {user_data[chat_id]['text_size']}"
                
                send_message_with_back_button(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد.{limit_info}{settings_info}\n\n✍️ متن استیکر بعدی را بفرست:\n\n📷 یا عکس جدید برای تغییر بکگراند بفرست:")
                
                # مهم: pack_name و background را حفظ کن تا استیکر بعدی در همان پک قرار بگیرد
                # step همچنان "text" باقی می‌ماند تا کاربر بتواند استیکر بعدی بسازد
            return True
    
    elif state.get("mode") == "advanced_design":
        step = state.get("step")
        
        # اگر کاربر در حالت طراحی پیشرفته است و متن فرستاده، به حالت free برو
        if step in ["color_selection", "font_selection", "size_selection", "position_selection", "background_color_selection", "effect_selection"]:
            # تنظیمات را بر اساس step ذخیره کن
            if step == "color_selection":
                user_data[chat_id]["text_color"] = text
            elif step == "font_selection":
                user_data[chat_id]["font_style"] = text
            elif step == "size_selection":
                user_data[chat_id]["text_size"] = text
            elif step == "position_selection":
                user_data[chat_id]["text_position"] = text
            elif step == "background_color_selection":
                user_data[chat_id]["background_style"] = text
            elif step == "effect_selection":
                user_data[chat_id]["text_effect"] = text
            
            # به حالت free برو
            user_data[chat_id]["mode"] = "free"
            
            # اگر pack_name نداریم، ابتدا آن را بپرس
            if not user_data[chat_id].get("pack_name"):
                user_data[chat_id]["step"] = "pack_name"
                send_message(chat_id, f"✅ تنظیمات ذخیره شد!\n\n📝 حالا یک نام برای پک استیکر خود انتخاب کن:\n\n💡 می‌تونید فارسی، انگلیسی یا حتی ایموجی بنویسید، ربات خودش تبدیلش می‌کنه!")
            else:
                # اگر pack_name داریم، مستقیماً به ساخت استیکر برو
                user_data[chat_id]["step"] = "text"
                send_message_with_back_button(chat_id, "✍️ حالا متن استیکرت رو بفرست:")
            return True
    
    return False


def send_as_sticker(chat_id, text, background_file_id=None):
    sticker_path = "sticker.png"
    
    # دریافت تنظیمات کاربر
    user_settings = {}
    if chat_id in user_data:
        user_settings = {
            "text_color": user_data[chat_id].get("text_color"),
            "background_style": user_data[chat_id].get("background_style"),
            "font_style": user_data[chat_id].get("font_style"),
            "text_size": user_data[chat_id].get("text_size"),
            "text_position": user_data[chat_id].get("text_position"),
            "text_effect": user_data[chat_id].get("text_effect")
        }
    
    ok = make_text_sticker(text, sticker_path, background_file_id, user_settings)
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
        # برعکس کردن ترتیب برای حفظ ترتیب طبیعی
        return reshaped[::-1]
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
            # اگر فقط یک کلمه است، آن را در وسط استیکر نگه دار
            return [text]
        
        # برای متن‌های طولانی فارسی، کلمات را از بالا به پایین مرتب کن
        lines = []
        for word in words:
            # هر کلمه را در یک خط جداگانه قرار بده
            lines.append(word)
        
        # برعکس کردن ترتیب کلمات تا کلمه اول بالا باشه
        return lines[::-1] if lines else [""]
    
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

def get_font(size, language="english", font_style="عادی"):
    """بارگذاری فونت بر اساس زبان و استایل"""
    # بررسی font_style
    if not font_style:
        font_style = "عادی"
    
    logger.info(f"✅ Getting font: size={size}, language={language}, style={font_style}")
    
    if language == "persian_arabic":
        # فونت‌های فارسی/عربی
        # برای فارسی، ابتدا فونت‌های موجود را امتحان کن
        font_paths = [
            "fonts/Vazirmatn-Regular.ttf",
            "fonts/IRANSans.ttf", 
            "fonts/Vazir.ttf",
            "fonts/Sahel.ttf",
            "fonts/Samim.ttf",
            "fonts/Tanha.ttf"
        ]
        
        # اگر فونت ضخیم یا نازک انتخاب شده، ابتدا آن‌ها را امتحان کن
        if "ضخیم" in font_style or "بولد" in font_style:
            font_paths = [
                "fonts/Vazirmatn-Bold.ttf",
                "fonts/IRANSans-Bold.ttf",
                "fonts/Vazir-Bold.ttf"
            ] + font_paths
        elif "نازک" in font_style or "لایت" in font_style:
            font_paths = [
                "fonts/Vazirmatn-Light.ttf",
                "fonts/IRANSans-Light.ttf",
                "fonts/Vazir-Light.ttf"
            ] + font_paths
        
        # اضافه کردن fallback ها
        font_paths.extend([
            "Vazirmatn-Regular.ttf",
            "IRANSans.ttf", 
            "Vazir.ttf",
            "Sahel.ttf",
            "Samim.ttf",
            "Tanha.ttf",
            "NotoSansArabic-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Windows/Fonts/arial.ttf"
        ])
    else:
        # فونت‌های انگلیسی
        font_paths = [
            "fonts/arial.ttf",
            "arial.ttf",
            "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/Windows/Fonts/arial.ttf"
        ]
        
        # اگر فونت ضخیم انتخاب شده، ابتدا آن‌ها را امتحان کن
        if "ضخیم" in font_style or "بولد" in font_style:
            font_paths = [
                "fonts/arial-bold.ttf",
                "arial-bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            ] + font_paths
        
        font_paths.extend([
            "NotoSans-Regular.ttf"
        ])
    
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, size)
            logger.info(f"Successfully loaded font: {font_path} with size: {size} for {language}")
            return font
        except (OSError, IOError):
            continue
    
    try:
        # تلاش برای بارگذاری فونت پیش‌فرض
        default_font = ImageFont.load_default()
        logger.warning(f"No custom font found, using default font for {language} with style {font_style}")
        return default_font
    except Exception as e:
        logger.error(f"Failed to load default font: {e}")
        # آخرین تلاش: فونت بدون استایل
        try:
            return ImageFont.load_default()
        except:
            return None

def make_text_sticker(text, path, background_file_id=None, user_settings=None):
    try:
        logger.info(f"Creating sticker with text: {text}")
        logger.info(f"User settings: {user_settings}")
        
        # بررسی متن خالی
        if not text or not text.strip():
            logger.error("❌ ERROR: Empty text provided")
            return False
        
        # تشخیص زبان
        try:
            language = detect_language(text)
            logger.info(f"✅ Language detected: {language}")
        except Exception as e:
            logger.error(f"❌ ERROR in language detection: {e}")
            language = "english"  # fallback
        
        # اصلاح متن فارسی/عربی
        try:
            if language == "persian_arabic":
                text = reshape_text(text)
                logger.info(f"✅ Persian text reshaped: {text}")
        except Exception as e:
            logger.error(f"❌ ERROR in text reshaping: {e}")
            # ادامه با متن اصلی
        
        # 🔥 رندر روی 256×256 و در پایان زوم 2x برای هر دو زبان
        img_size = 256
        img = Image.new("RGBA", (img_size, img_size), (255, 255, 255, 0))

        # 📌 پس‌زمینه: ابتدا تلاش برای قالب یا رنگ انتخابی، سپس عکس کاربر
        background_applied = False
        template_bg = None
        if user_settings and "background_style" in user_settings:
            template_bg = user_settings.get("background_style")
            logger.info(f"Checking template background: {template_bg}")
            # اگر مسیر فایل قالب است
            if isinstance(template_bg, str) and template_bg.startswith("templates/"):
                try:
                    path_try = template_bg
                    # اگر پسوند png موجود نبود، jpg را امتحان کن و برعکس
                    if not os.path.exists(path_try):
                        if path_try.lower().endswith(".png"):
                            alt = path_try[:-4] + ".jpg"
                        elif path_try.lower().endswith(".jpg") or path_try.lower().endswith(".jpeg"):
                            alt = os.path.splitext(path_try)[0] + ".png"
                        else:
                            alt = path_try + ".jpg"
                        if os.path.exists(alt):
                            logger.info(f"Template alt background found: {alt}")
                            path_try = alt
                    if os.path.exists(path_try):
                        bg = Image.open(path_try).convert("RGBA")
                        bg = bg.resize((img_size, img_size))
                        img.paste(bg, (0, 0))
                        background_applied = True
                        logger.info(f"Template background loaded: {path_try}")
                    else:
                        logger.warning(f"Template background not found: {template_bg}")
                except Exception as e:
                    logger.error(f"Error loading template background: {e}")
            # اگر یکی از گزینه‌های رنگی منو باشد
            elif isinstance(template_bg, str) and (template_bg.startswith("🖼️") or template_bg in ["سفید","مشکی","آبی","قرمز","سبز","شفاف"]):
                color_map_bg = {
                    "🖼️ سفید": (255,255,255,255),
                    "🖼️ مشکی": (0,0,0,255),
                    "🖼️ آبی": (0,0,255,255),
                    "🖼️ قرمز": (255,0,0,255),
                    "🖼️ سبز": (0,255,0,255),
                    "🖼️ شفاف": (255,255,255,0),
                    "سفید": (255,255,255,255),
                    "مشکی": (0,0,0,255),
                    "آبی": (0,0,255,255),
                    "قرمز": (255,0,0,255),
                    "سبز": (0,255,0,255),
                    "شفاف": (255,255,255,0)
                }
                if template_bg in color_map_bg:
                    img = Image.new("RGBA", (img_size, img_size), color_map_bg[template_bg])
                    background_applied = True
                    logger.info(f"Color background applied: {template_bg}")
                elif template_bg == "🖼️ گرادیانت":
                    # گرادیانت ساده عمودی سفید→خاکستری
                    grad = Image.new("RGBA", (img_size, img_size))
                    for y_px in range(img_size):
                        shade = int(255 * (y_px / (img_size-1)))
                        for x_px in range(img_size):
                            grad.putpixel((x_px, y_px), (shade, shade, shade, 255))
                    img.paste(grad, (0,0))
                    background_applied = True
                    logger.info("Gradient background applied")
                elif template_bg == "🖼️ الگو":
                    # الگوی ساده شطرنجی خاکستری
                    tile = 32
                    pattern = Image.new("RGBA", (img_size, img_size), (220,220,220,255))
                    draw_pat = ImageDraw.Draw(pattern)
                    for yy in range(0, img_size, tile):
                        for xx in range(0, img_size, tile):
                            if (xx//tile + yy//tile) % 2 == 0:
                                draw_pat.rectangle([xx, yy, xx+tile, yy+tile], fill=(200,200,200,255))
                    img.paste(pattern, (0,0))
                    background_applied = True
                    logger.info("Pattern background applied")
            else:
                logger.info(f"Template background not applicable: {template_bg}")

        # اگر هنوز پس‌زمینه اعمال نشده، از عکس کاربر استفاده کن
        if not background_applied and background_file_id:
            logger.info(f"Trying user photo background: file_id={background_file_id}")
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
                        background_applied = True
                        logger.info("Background image loaded successfully")
                    else:
                        logger.error(f"Failed to download user background: status={resp.status_code}")
                else:
                    logger.error(f"getFile not ok for background_file_id: {file_info}")
            except Exception as e:
                logger.error(f"Error loading background: {e}")

        if not background_applied:
            logger.info("No background applied (template/user). Using transparent background.")

        draw = ImageDraw.Draw(img)
        
        # 📌 تنظیمات فونت و باکس متن (بهینه‌سازی برای متن فارسی)
        # تنظیم اندازه فونت از تنظیمات کاربر
        if user_settings and "text_size" in user_settings and user_settings["text_size"]:
            size_text = user_settings["text_size"]
            if "خیلی کوچک" in size_text:
                initial_font_size = 20 if language == "persian_arabic" else 150
            elif "کوچک" in size_text:
                initial_font_size = 30 if language == "persian_arabic" else 200
            elif "متوسط" in size_text:
                initial_font_size = 50 if language == "persian_arabic" else 300
            elif "بزرگ" in size_text:
                initial_font_size = 70 if language == "persian_arabic" else 400
            elif "خیلی بزرگ" in size_text:
                initial_font_size = 90 if language == "persian_arabic" else 500
            else:
                initial_font_size = 50 if language == "persian_arabic" else 300
        else:
            if language == "persian_arabic":
                initial_font_size = 50   # کاهش بیشتر برای فارسی
            else:
                initial_font_size = 300  # فونت انگلیسی
        
        if language == "persian_arabic":
            min_font_size = 12       # کاهش بیشتر برای فارسی
        else:
            min_font_size = 120      # حداقل فونت انگلیسی
        max_width = 110              # کاهش بیشتر برای فارسی
        max_height = 110             # کاهش بیشتر برای فارسی
        
        # تنظیم فونت از تنظیمات کاربر
        font_style = "عادی"
        if user_settings and "font_style" in user_settings and user_settings["font_style"]:
            font_style = user_settings["font_style"]
        
        logger.info(f"✅ Font style: {font_style}")
        font = get_font(initial_font_size, language, font_style)
        
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
            font = get_font(font_size, language, font_style)
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
            line_spacing = max(int(font_size * 0.1), 2)  # فاصله متوسط برای فارسی (کلمات از بالا به پایین)
        else:
            line_spacing = max(int(font_size * 0.15), 3)  # فاصله متوسط برای انگلیسی
        
        try:
            lines = wrap_text_multiline(draw, text, font, max_width, is_rtl=(language=="persian_arabic"))
            block_w, block_h = measure_multiline_block(draw, lines, font, line_spacing)
        except Exception as e:
            logger.error(f"Error in text wrapping: {e}")
            # fallback: متن را در یک خط قرار بده
            lines = [text]
            block_w, block_h = _measure_text(draw, text, font)
        x = (img_size - block_w) / 2
        # وسط‌چین عمودی برای هر دو زبان
        is_rtl = (language == "persian_arabic")
        y = (img_size - block_h) / 2

        # 📌 حاشیه بر اساس زبان (کاهش برای متن کوچک‌تر)
        if language == "persian_arabic":
            outline_thickness = 2  # فارسی: حاشیه نازک
        else:
            outline_thickness = 1  # انگلیسی: حاشیه خیلی نازک
        
        # رنگ متن از تنظیمات کاربر
        text_color = "#000000"  # پیش‌فرض
        if user_settings and "text_color" in user_settings and user_settings["text_color"]:
            color_text = user_settings["text_color"]
            # تبدیل نام رنگ به کد hex
            color_map = {
                "قرمز": "#FF0000",
                "آبی": "#0000FF", 
                "سبز": "#00FF00",
                "زرد": "#FFFF00",
                "بنفش": "#800080",
                "نارنجی": "#FFA500",
                "صورتی": "#FFC0CB",
                "مشکی": "#000000",
                "سفید": "#FFFFFF",
                "خاکستری": "#808080"
            }
            text_color = color_map.get(color_text, "#000000")
            logger.info(f"✅ Text color: {color_text} -> {text_color}")
        else:
            logger.info(f"✅ Using default text color: {text_color}")
        
        # موقعیت متن از تنظیمات کاربر
        align_h = "center"
        align_v = "middle"
        if user_settings and user_settings.get("text_position"):
            pos = user_settings["text_position"]
            if "بالا" in pos: align_v = "top"
            if "پایین" in pos: align_v = "bottom"
            if "راست" in pos: align_h = "right"
            if "چپ" in pos: align_h = "left"
        
        # محاسبه X,Y شروع بر اساس تراز انتخابی
        if align_h == "left":
            x = 10
        elif align_h == "right":
            x = img_size - block_w - 10
        # center پیش‌فرض
        if align_v == "top":
            y = 10
        elif align_v == "bottom":
            y = img_size - block_h - 10
        # middle پیش‌فرض
        
        # افکت‌های متن
        effect = None
        if user_settings and user_settings.get("text_effect"):
            effect = user_settings["text_effect"]
        
        # رسم هر خط با حاشیه و متن
        current_y = y
        for line in lines:
            try:
                w_line, h_line = _measure_text(draw, line, font)
                # محاسبه X برای هر خط با توجه به تراز افقی
                if align_h == "left":
                    line_x = x
                elif align_h == "right":
                    line_x = x + (block_w - w_line)
                else:
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
                            # سایه/هاله: قبل از متن اصلی اجرا می‌شود
                            if effect == "✨ سایه":
                                draw.text((line_x + dx, current_y + dy), line, font=font, fill=(0,0,0,180))
                            elif effect == "✨ نور":
                                draw.text((line_x + dx, current_y + dy), line, font=font, fill=(255,255,255,120))
                            else:
                                draw.text((line_x + dx, current_y + dy), line, font=font, fill="white")
                        except Exception:
                            pass
                # متن اصلی
                try:
                    if effect == "✨ شفاف":
                        # کمی شفاف‌تر
                        rgba = Image.new("RGBA", (img_size, img_size))
                        d2 = ImageDraw.Draw(rgba)
                        d2.text((line_x, current_y), line, fill=text_color, font=font)
                        img.alpha_composite(rgba, (0,0))
                    else:
                        draw.text((line_x, current_y), line, fill=text_color, font=font)
                except Exception as e:
                    logger.error(f"Error drawing line with font: {e}")
                    try:
                        draw.text((line_x, current_y), line, fill=text_color)
                    except Exception as e2:
                        logger.error(f"Error drawing line without font: {e2}")
                        # آخرین تلاش: متن ساده
                        draw.text((line_x, current_y), "ERROR", fill=text_color)
                current_y += h_line + line_spacing
            except Exception as e:
                logger.error(f"Error processing line '{line}': {e}")
                continue

        # 🔥 زوم 2x برای هر دو زبان جهت بهبود کیفیت لبه‌ها (Telegram فقط 512x512 قبول می‌کنه)
        final_img = img.resize((512, 512), Image.LANCZOS)

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
            ["🎨 طراحی پیشرفته", "📚 قالب‌های آماده"],
            ["📝 تاریخچه", "⚙️ تنظیمات"],
            ["ℹ️ درباره", "📞 پشتیبانی"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": tr(chat_id, "main_menu", "👋 خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:"),
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

def send_message_with_back_button(chat_id, text):
    """ارسال پیام با دکمه بازگشت"""
    keyboard = {
        "keyboard": [
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard
    })

def show_advanced_design_menu(chat_id):
    """نمایش منوی طراحی پیشرفته"""
    keyboard = {
        "keyboard": [
            ["🎨 انتخاب رنگ متن", "📝 انتخاب فونت"],
            ["📏 اندازه متن", "📍 موقعیت متن"],
            ["🖼️ رنگ پس‌زمینه", "✨ افکت‌های ویژه"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "🎨 منوی طراحی پیشرفته:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_template_menu(chat_id):
    """نمایش منوی قالب‌های آماده"""
    keyboard = {
        "keyboard": [
            ["🎉 تولد", "💒 عروسی", "🎊 جشن"],
            ["💝 عاشقانه", "😄 خنده‌دار", "🔥 هیجان‌انگیز"],
            ["📚 آموزشی", "💼 کاری", "🏠 خانوادگی"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "📚 قالب‌های آماده:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_history(chat_id):
    """نمایش تاریخچه استیکرها"""
    if chat_id not in user_data or not user_data[chat_id].get("created_packs"):
        send_message_with_back_button(chat_id, "📝 شما هنوز استیکری نساخته‌اید.")
        return
    
    packs = user_data[chat_id]["created_packs"]
    message = "📝 تاریخچه استیکرهای شما:\n\n"
    
    for i, pack in enumerate(packs, 1):
        message += f"{i}. {pack['title']}\n"
    
    send_message_with_back_button(chat_id, message)

def show_settings_menu(chat_id):
    """نمایش منوی تنظیمات"""
    keyboard = {
        "keyboard": [
            ["🌍 زبان"],
            ["💾 ذخیره قالب", "📤 اشتراک‌گذاری"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "⚙️ تنظیمات:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_color_menu(chat_id):
    """نمایش منوی انتخاب رنگ متن"""
    keyboard = {
        "keyboard": [
            ["🔴 قرمز", "🔵 آبی", "🟢 سبز"],
            ["⚫ مشکی", "⚪ سفید", "🟡 زرد"],
            ["🟣 بنفش", "🟠 نارنجی", "🟤 قهوه‌ای"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "🎨 انتخاب رنگ متن:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_font_menu(chat_id):
    """نمایش منوی انتخاب فونت"""
    keyboard = {
        "keyboard": [
            ["📝 فونت عادی", "📝 فونت ضخیم"],
            ["📝 فونت نازک", "📝 فونت کج"],
            ["📝 فونت فانتزی", "📝 فونت کلاسیک"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "📝 انتخاب فونت:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_size_menu(chat_id):
    """نمایش منوی اندازه متن"""
    keyboard = {
        "keyboard": [
            ["📏 کوچک", "📏 متوسط", "📏 بزرگ"],
            ["📏 خیلی کوچک", "📏 خیلی بزرگ"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "📏 انتخاب اندازه متن:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_position_menu(chat_id):
    """نمایش منوی موقعیت متن"""
    keyboard = {
        "keyboard": [
            ["📍 بالا", "📍 وسط", "📍 پایین"],
            ["📍 راست", "📍 چپ", "📍 وسط‌چین"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "📍 انتخاب موقعیت متن:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_background_color_menu(chat_id):
    """نمایش منوی رنگ پس‌زمینه"""
    keyboard = {
        "keyboard": [
            ["🖼️ شفاف", "🖼️ سفید", "🖼️ مشکی"],
            ["🖼️ آبی", "🖼️ قرمز", "🖼️ سبز"],
            ["🖼️ گرادیانت", "🖼️ الگو"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "🖼️ انتخاب رنگ پس‌زمینه:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_effects_menu(chat_id):
    """نمایش منوی افکت‌های ویژه"""
    keyboard = {
        "keyboard": [
            ["✨ سایه", "✨ نور", "✨ براق"],
            ["✨ مات", "✨ شفاف", "✨ انعکاس"],
            ["✨ چرخش", "✨ موج", "✨ پرش"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "✨ انتخاب افکت‌های ویژه:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def apply_template(chat_id, template_name):
    """اعمال قالب آماده"""
    templates = {
        "🎉 تولد": {"color": "#FFFF00", "bg": "templates/birthday_bg.png", "font": "📝 فونت فانتزی", "size": "📏 بزرگ"},
        "💒 عروسی": {"color": "#FFFFFF", "bg": "templates/wedding_bg.png", "font": "📝 فونت کلاسیک", "size": "📏 متوسط"},
        "🎊 جشن": {"color": "#800080", "bg": "templates/party_bg.png", "font": "📝 فونت ضخیم", "size": "📏 بزرگ"},
        "💝 عاشقانه": {"color": "#FF0000", "bg": "templates/love_bg.png", "font": "📝 فونت کج", "size": "📏 متوسط"},
        "😄 خنده‌دار": {"color": "#FFA500", "bg": "templates/funny_bg.png", "font": "📝 فونت فانتزی", "size": "📏 بزرگ"},
        "🔥 هیجان‌انگیز": {"color": "#FF0000", "bg": "templates/exciting_bg.png", "font": "📝 فونت ضخیم", "size": "📏 خیلی بزرگ"},
        "📚 آموزشی": {"color": "#0000FF", "bg": "templates/education_bg.png", "font": "📝 فونت عادی", "size": "📏 متوسط"},
        "💼 کاری": {"color": "#000000", "bg": "templates/work_bg.png", "font": "📝 فونت کلاسیک", "size": "📏 متوسط"},
        "🏠 خانوادگی": {"color": "#00FF00", "bg": "templates/family_bg.png", "font": "📝 فونت عادی", "size": "📏 متوسط"}
    }
    
    if template_name in templates:
        template = templates[template_name]
        
        # تنظیم تنظیمات کاربر
        if chat_id not in user_data:
            user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
        
        # تبدیل hex کد به نام رنگ فارسی
        color_hex = template["color"]
        color_name = "مشکی"  # پیش‌فرض
        if color_hex == "#FFFF00":
            color_name = "زرد"
        elif color_hex == "#FFFFFF":
            color_name = "سفید"
        elif color_hex == "#800080":
            color_name = "بنفش"
        elif color_hex == "#FF0000":
            color_name = "قرمز"
        elif color_hex == "#FFA500":
            color_name = "نارنجی"
        elif color_hex == "#0000FF":
            color_name = "آبی"
        elif color_hex == "#000000":
            color_name = "مشکی"
        elif color_hex == "#00FF00":
            color_name = "سبز"
        
        user_data[chat_id]["text_color"] = color_name
        user_data[chat_id]["background_style"] = template["bg"]
        user_data[chat_id]["font_style"] = template["font"]
        user_data[chat_id]["text_size"] = template["size"]
        user_data[chat_id]["text_position"] = "📍 وسط"
        user_data[chat_id]["text_effect"] = "✨ سایه"
        
        # رفتن به حالت ساخت استیکر
        user_data[chat_id]["mode"] = "free"
        
        # اگر pack_name نداریم، ابتدا آن را بپرس
        if not user_data[chat_id].get("pack_name"):
            user_data[chat_id]["step"] = "pack_name"
            send_message(chat_id, f"✅ قالب '{template_name}' اعمال شد!\n\n🎨 رنگ: {color_name}\n🖼️ پس‌زمینه: {template['bg']}\n📝 فونت: {template['font']}\n📏 اندازه: {template['size']}\n\n📝 حالا یک نام برای پک استیکر خود انتخاب کن:")
        else:
            user_data[chat_id]["step"] = "text"
            send_message_with_back_button(chat_id, f"✅ قالب '{template_name}' اعمال شد!\n\n🎨 رنگ: {color_name}\n🖼️ پس‌زمینه: {template['bg']}\n📝 فونت: {template['font']}\n📏 اندازه: {template['size']}\n\nحالا متن خود را بفرستید:")
    else:
        send_message_with_back_button(chat_id, "❌ قالب پیدا نشد!")

def set_dark_mode(chat_id, is_dark):
    """تنظیم حالت تاریک/روشن"""
    mode = "تاریک" if is_dark else "روشن"
    send_message_with_back_button(chat_id, f"✅ حالت {mode} فعال شد!")

def toggle_notifications(chat_id):
    """تغییر وضعیت اعلان‌ها"""
    send_message_with_back_button(chat_id, "✅ وضعیت اعلان‌ها تغییر کرد!")

def show_language_menu(chat_id):
    """نمایش منوی زبان"""
    keyboard = {
        "keyboard": [
            ["🇮🇷 فارسی", "🇺🇸 انگلیسی"],
            ["🇸🇦 عربی", "🇹🇷 ترکی"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": tr(chat_id, "choose_lang", "🌍 انتخاب زبان:\n\nانتخاب کنید:"),
        "reply_markup": keyboard
    })

def save_template(chat_id):
    """ذخیره قالب"""
    send_message_with_back_button(chat_id, "✅ قالب ذخیره شد!")

def share_sticker(chat_id):
    """اشتراک‌گذاری استیکر"""
    send_message_with_back_button(chat_id, "📤 لینک اشتراک‌گذاری:\n\n🔗 https://t.me/your_bot")

if __name__ == "__main__":
    load_locales()
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        resp = requests.get(API + f"setWebhook?url={webhook_url}")
        logger.info(f"setWebhook: {resp.json()}")
    else:
        logger.warning("⚠️ APP_URL is not set. Webhook not registered.")

    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
