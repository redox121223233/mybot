import os
import logging
import re
import time
import json
import tempfile
import subprocess
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

# --- Admin Config ---
ADMIN_ID = 6053579919  # ایدی ادمین اصلی
SUPPORT_ID = "@onedaytoalive"  # ایدی پشتیبانی

# --- Payment Config ---
CARD_NUMBER = os.environ.get("CARD_NUMBER", "1234-5678-9012-3456")  # شماره کارت
CARD_NAME = os.environ.get("CARD_NAME", "نام شما")  # نام صاحب کارت

# دیتابیس ساده در حافظه
user_data = {}
subscription_data = {}  # داده‌های اشتراک
pending_payments = {}   # پرداخت‌های در انتظار
feedback_data = {}      # بازخوردهای کاربران

# فایل ذخیره‌سازی داده‌ها
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "user_data.json")
SUBSCRIPTION_FILE = os.path.join(BASE_DIR, "subscriptions.json")
PAYMENTS_FILE = os.path.join(BASE_DIR, "pending_payments.json")
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback_data.json")

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

# طرح‌های اشتراک
SUBSCRIPTION_PLANS = {
    "1month": {"price": 100, "days": 30, "title": "یک ماهه"},
    "3months": {"price": 250, "days": 90, "title": "سه ماهه"},
    "12months": {"price": 350, "days": 365, "title": "یک ساله"}
}

def load_locales():
    """Optionally override LOCALES with files in locales/*.json"""
    try:
        import glob
        # مسیر locales نسبی به فایل bot.py
        locales_dir = os.path.join(BASE_DIR, "locales")
        for path in glob.glob(os.path.join(locales_dir, "*.json")):
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
                # ابتدا کنار bot.py سپس یک پوشه بالاتر (ریشه پروژه)
                cand1 = os.path.join(BASE_DIR, fname)
                cand2 = os.path.join(BASE_DIR, "..", fname)
                use_path = None
                if os.path.exists(cand1):
                    use_path = cand1
                elif os.path.exists(cand2):
                    use_path = cand2
                if use_path:
                    with open(use_path, "r", encoding="utf-8") as f:
                        LOCALES[code] = json.load(f)
                    logger.info(f"Loaded flat locale: {code} from {use_path}")
            except Exception as e:
                logger.error(f"Failed to load flat locale {fname}: {e}")
    except Exception as e:
        logger.error(f"Error scanning locales: {e}")

def get_lang(chat_id):
    return user_data.get(chat_id, {}).get("lang", "fa")

def tr(chat_id, key, fallback_text):
    lang = get_lang(chat_id)
    return LOCALES.get(lang, {}).get(key, fallback_text)

def tr_lang(lang, key, fallback_text):
    """ترجمه بر اساس زبان مشخص"""
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

def load_subscription_data():
    """بارگذاری داده‌های اشتراک از فایل"""
    global subscription_data
    try:
        if os.path.exists(SUBSCRIPTION_FILE):
            with open(SUBSCRIPTION_FILE, 'r', encoding='utf-8') as f:
                subscription_data = json.load(f)
                logger.info(f"Loaded subscription data: {len(subscription_data)} users")
        else:
            subscription_data = {}
    except Exception as e:
        logger.error(f"Error loading subscription data: {e}")
        subscription_data = {}

def save_subscription_data():
    """ذخیره داده‌های اشتراک در فایل"""
    try:
        with open(SUBSCRIPTION_FILE, 'w', encoding='utf-8') as f:
            json.dump(subscription_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved subscription data: {len(subscription_data)} users")
    except Exception as e:
        logger.error(f"Error saving subscription data: {e}")

def load_pending_payments():
    """بارگذاری پرداخت‌های در انتظار از فایل"""
    global pending_payments
    try:
        if os.path.exists(PAYMENTS_FILE):
            with open(PAYMENTS_FILE, 'r', encoding='utf-8') as f:
                pending_payments = json.load(f)
                logger.info(f"Loaded pending payments: {len(pending_payments)} payments")
        else:
            pending_payments = {}
    except Exception as e:
        logger.error(f"Error loading pending payments: {e}")
        pending_payments = {}

def save_pending_payments():
    """ذخیره پرداخت‌های در انتظار در فایل"""
    try:
        with open(PAYMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(pending_payments, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved pending payments: {len(pending_payments)} payments")
    except Exception as e:
        logger.error(f"Error saving pending payments: {e}")

def load_feedback_data():
    """بارگذاری بازخوردهای کاربران از فایل"""
    global feedback_data
    try:
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
                logger.info(f"Loaded feedback data: {len(feedback_data)} feedbacks")
        else:
            feedback_data = {}
    except Exception as e:
        logger.error(f"Error loading feedback data: {e}")
        feedback_data = {}

def save_feedback_data():
    """ذخیره بازخوردهای کاربران در فایل"""
    try:
        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved feedback data: {len(feedback_data)} feedbacks")
    except Exception as e:
        logger.error(f"Error saving feedback data: {e}")

# بارگذاری داده‌ها در شروع
load_user_data()
load_subscription_data()
load_pending_payments()
load_feedback_data()
load_locales()  # بارگذاری فایل‌های ترجمه

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

    # 📌 پردازش دستورات ادمین
    if "text" in msg and msg["text"].startswith("/admin"):
        handle_admin_command(chat_id, msg["text"])
        return "ok"

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

        # 📌 پردازش دکمه‌های اشتراک
        if text == "⭐ اشتراک":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_subscription_menu(chat_id)
            return "ok"
        
        # پردازش دکمه‌های طرح اشتراک
        if text in ["📦 یک ماهه - ۱۰۰ تومان", "📦 سه ماهه - ۲۵۰ تومان", "📦 یک ساله - ۳۵۰ تومان"]:
            if "یک ماهه" in text:
                plan = "1month"
            elif "سه ماهه" in text:
                plan = "3months" 
            else:
                plan = "12months"
            show_payment_info(chat_id, plan)
            return "ok"

        # دکمه‌های قابلیت‌های اشتراکی
        if text in ["🎞 تبدیل استیکر ویدیویی به گیف", "🎥 تبدیل گیف به استیکر ویدیویی", 
                   "🖼 تبدیل عکس به استیکر", "📂 تبدیل استیکر به عکس", 
                   "🌃 تبدیل PNG به استیکر", "🗂 تبدیل فایل ویدیو", "🎥 تبدیل ویدیو مسیج"]:
            if not is_subscribed(chat_id):
                send_message(chat_id, "⭐ این قابلیت فقط برای کاربران اشتراکی است!\n\nبرای خرید اشتراک از منوی اصلی استفاده کنید.")
                return "ok"
            handle_premium_feature(chat_id, text)
            return "ok"

        # دکمه ارسال رسید
        if text == "📸 ارسال رسید":
            user_data[chat_id] = user_data.get(chat_id, {})
            user_data[chat_id]["step"] = "waiting_receipt"
            send_message_with_back_button(chat_id, "📸 لطفاً عکس رسید پرداخت را ارسال کنید:")
            return "ok"

        # پردازش بازخورد
        if text in ["👍 عالی بود!", "👎 خوب نبود"]:
            handle_feedback(chat_id, text)
            return "ok"
        
        # دکمه‌های اضافی بعد از بازخورد
        if text == "✍️ متن بعدی":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            
            # بررسی محدودیت استیکر
            remaining, next_reset = check_sticker_limit(chat_id)
            if remaining <= 0:
                next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                send_message(chat_id, f"⏰ محدودیت روزانه شما تمام شده!\n\n🔄 زمان بعدی: {next_reset_time}\n\n💎 برای ساخت استیکر نامحدود، اشتراک تهیه کنید.")
                return "ok"
            
            send_message_with_back_button(chat_id, "✍️ متن استیکر بعدی را بفرست:")
            return "ok"
        
        if text == "📷 تغییر بکگراند":
            # بررسی عضویت در کانال
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            
            send_message_with_back_button(chat_id, "📷 عکس جدید برای بکگراند بفرست:")
            if chat_id in user_data:
                user_data[chat_id]["step"] = "background"
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

        # پردازش دکمه‌های افکت‌های ویژه
        if text in ["✨ سایه", "✨ نور", "✨ براق", "✨ مات", "✨ شفاف", "✨ انعکاس", "✨ چرخش", "✨ موج", "✨ پرش"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["text_effect"] = text
            user_data[chat_id]["mode"] = "free"
            if not user_data[chat_id].get("pack_name"):
                user_data[chat_id]["step"] = "pack_name"
                send_message(chat_id, f"✅ افکت {text} انتخاب شد!\n\n📝 حالا یک نام برای پک استیکر خود انتخاب کن:")
            else:
                user_data[chat_id]["step"] = "text"
                send_message_with_back_button(chat_id, f"✅ افکت {text} انتخاب شد!\n\n✍️ حالا متن استیکرت رو بفرست:")
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
            send_message(chat_id, f"📞 برای پشتیبانی با {SUPPORT_ID} در تماس باش.\n\nاگر مشکلی پیش آمد، حتماً پیوی بزنید!")

        # پردازش حالت کاربر (بعد از دکمه‌ها)
        if process_user_state(chat_id, text):
            return "ok"

    # 📌 پردازش عکس
    elif "photo" in msg:
        state = user_data.get(chat_id, {})
        
        # بررسی ارسال رسید
        if state.get("step") == "waiting_receipt":
            photos = msg.get("photo", [])
            if photos:
                file_id = photos[-1].get("file_id")
                if file_id:
                    # ذخیره رسید در پرداخت‌های در انتظار
                    payment_id = f"{chat_id}_{int(time.time())}"
                    user_info = requests.get(API + f"getChat?chat_id={chat_id}").json()
                    username = user_info.get("result", {}).get("username", f"user_{chat_id}")
                    first_name = user_info.get("result", {}).get("first_name", "User")
                    
                    pending_payments[payment_id] = {
                        "user_id": chat_id,
                        "username": username,
                        "first_name": first_name,
                        "receipt_file_id": file_id,
                        "timestamp": time.time(),
                        "plan": state.get("selected_plan", "1month")
                    }
                    save_pending_payments()
                    
                    # اطلاع به ادمین
                    admin_message = f"""🔔 رسید جدید دریافت شد!

👤 کاربر: {first_name} (@{username if username != f'user_{chat_id}' else 'بدون یوزرنیم'})
🆔 ایدی: {chat_id}
📦 طرح: {SUBSCRIPTION_PLANS[state.get('selected_plan', '1month')]['title']}
💰 مبلغ: {SUBSCRIPTION_PLANS[state.get('selected_plan', '1month')]['price']} تومان
⏰ زمان: {time.strftime('%Y-%m-%d %H:%M:%S')}

برای تایید: /admin add {chat_id} {SUBSCRIPTION_PLANS[state.get('selected_plan', '1month')]['days']}"""
                    
                    # ارسال رسید به ادمین
                    try:
                        requests.post(API + "sendPhoto", data={
                            "chat_id": ADMIN_ID,
                            "photo": file_id,
                            "caption": admin_message
                        })
                    except Exception as e:
                        logger.error(f"Error sending receipt to admin: {e}")
                    
                    # پاسخ به کاربر
                    user_data[chat_id]["step"] = None
                    send_message_with_back_button(chat_id, f"✅ رسید شما دریافت شد!\n\n⏳ لطفاً منتظر تایید پشتیبانی باشید.\n\n📞 در صورت عدم پاسخ، با {SUPPORT_ID} تماس بگیرید.")
                    return "ok"
        
        # پردازش عکس برای استیکر
        if state.get("mode") == "free":
            photos = msg.get("photo", [])
            if photos:
                # انتخاب بهترین کیفیت عکس (آخرین عکس معمولاً بالاترین کیفیت است)
                photo = photos[-1]
                file_id = photo.get("file_id")
                file_size = photo.get("file_size", 0)
                
                if file_id:
                    # بررسی حجم عکس
                    if file_size > 20 * 1024 * 1024:  # 20MB
                        send_message_with_back_button(chat_id, "❌ عکس خیلی بزرگ است! (حداکثر 20MB)\n\n💡 راه حل:\n• از عکس با کیفیت کمتر استفاده کنید\n• عکس را فشرده کنید\n• از ابزارهای آنلاین برای کاهش حجم استفاده کنید")
                        return "ok"
                    
                    if state.get("step") == "background":
                        # عکس اول برای بکگراند
                        user_data[chat_id]["background"] = file_id
                        user_data[chat_id]["step"] = "text"
                        
                        # اطلاع‌رسانی در مورد حجم عکس
                        size_info = ""
                        if file_size > 5 * 1024 * 1024:  # 5MB
                            size_info = "\n\n⚠️ عکس شما بزرگ است، ممکن است پردازش کمی طول بکشد."
                        elif file_size > 2 * 1024 * 1024:  # 2MB
                            size_info = "\n\n📷 عکس با کیفیت خوب دریافت شد."
                        
                        send_message_with_back_button(chat_id, f"✅ بکگراند تنظیم شد!{size_info}\n\n✍️ حالا متن استیکرت رو بفرست:")
                        
                    elif state.get("step") == "text":
                        # تغییر بکگراند در حین ساخت استیکر
                        user_data[chat_id]["background"] = file_id
                        
                        # اطلاع‌رسانی در مورد حجم عکس
                        size_info = ""
                        if file_size > 5 * 1024 * 1024:  # 5MB
                            size_info = "\n⚠️ عکس بزرگ است، پردازش ممکن است کمی طول بکشد."
                        
                        send_message_with_back_button(chat_id, f"✅ بکگراند تغییر کرد!{size_info}\n✍️ متن استیکر بعدی را بفرست:")
        
        # پردازش عکس برای قابلیت‌های اشتراکی
        handle_premium_file(chat_id, "photo", msg.get("photo", []))

    # 📌 پردازش استیکر
    elif "sticker" in msg:
        handle_premium_file(chat_id, "sticker", msg["sticker"])

    # 📌 پردازش ویدیو
    elif "video" in msg:
        handle_premium_file(chat_id, "video", msg["video"])

    # 📌 پردازش انیمیشن (GIF)
    elif "animation" in msg:
        handle_premium_file(chat_id, "animation", msg["animation"])

    # 📌 پردازش ویدیو نوت
    elif "video_note" in msg:
        handle_premium_file(chat_id, "video_note", msg["video_note"])

    # 📌 پردازش فایل
    elif "document" in msg:
        handle_premium_file(chat_id, "document", msg["document"])

    return "ok"

def handle_premium_feature(chat_id, feature):
    """پردازش قابلیت‌های اشتراکی"""
    if chat_id not in user_data:
        user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
    
    if feature == "🎞 تبدیل استیکر ویدیویی به گیف":
        user_data[chat_id]["mode"] = "video_sticker_to_gif"
        user_data[chat_id]["step"] = "waiting_file"
        send_message_with_back_button(chat_id, "🎞 لطفاً استیکر ویدیویی خود را ارسال کنید:")
    
    elif feature == "🎥 تبدیل گیف به استیکر ویدیویی":
        user_data[chat_id]["mode"] = "gif_to_video_sticker"
        user_data[chat_id]["step"] = "waiting_file"
        send_message_with_back_button(chat_id, "🎥 لطفاً فایل GIF خود را ارسال کنید:")
    
    elif feature == "🖼 تبدیل عکس به استیکر":
        user_data[chat_id]["mode"] = "photo_to_sticker"
        user_data[chat_id]["step"] = "waiting_file"
        send_message_with_back_button(chat_id, "🖼 لطفاً عکس خود را ارسال کنید:")
    
    elif feature == "📂 تبدیل استیکر به عکس":
        user_data[chat_id]["mode"] = "sticker_to_photo"
        user_data[chat_id]["step"] = "waiting_file"
        send_message_with_back_button(chat_id, "📂 لطفاً استیکر خود را ارسال کنید:")
    
    elif feature == "🌃 تبدیل PNG به استیکر":
        user_data[chat_id]["mode"] = "png_to_sticker"
        user_data[chat_id]["step"] = "waiting_file"
        send_message_with_back_button(chat_id, "🌃 لطفاً فایل PNG خود را ارسال کنید:")
    
    elif feature == "🗂 تبدیل فایل ویدیو":
        user_data[chat_id]["mode"] = "file_to_video"
        user_data[chat_id]["step"] = "waiting_file"
        send_message_with_back_button(chat_id, "🗂 لطفاً فایل ویدیو خود را ارسال کنید:")
    
    elif feature == "🎥 تبدیل ویدیو مسیج":
        user_data[chat_id]["mode"] = "video_message_to_video"
        user_data[chat_id]["step"] = "waiting_file"
        send_message_with_back_button(chat_id, "🎥 لطفاً ویدیو مسیج خود را ارسال کنید:")
    
    save_user_data()

def handle_premium_file(chat_id, file_type, file_data):
    """پردازش فایل‌های قابلیت‌های اشتراکی"""
    state = user_data.get(chat_id, {})
    mode = state.get("mode")
    
    if not mode or state.get("step") != "waiting_file":
        return
    
    if not is_subscribed(chat_id):
        send_message(chat_id, "⭐ این قابلیت فقط برای کاربران اشتراکی است!")
        return
    
    try:
        # دریافت file_id بسته به نوع فایل
        if file_type == "photo":
            file_id = file_data[-1]["file_id"] if file_data else None
            file_size = file_data[-1].get("file_size", 0) if file_data else 0
        elif file_type in ["sticker", "video", "animation", "video_note", "document"]:
            file_id = file_data["file_id"] if file_data else None
            file_size = file_data.get("file_size", 0) if file_data else 0
        else:
            file_id = None
            file_size = 0
        
        if not file_id:
            send_message(chat_id, "❌ خطا در دریافت فایل!")
            return
        
        # بررسی حجم فایل قبل از دانلود
        if file_size > 20 * 1024 * 1024:  # 20MB
            send_message(chat_id, "❌ فایل خیلی بزرگ است! (حداکثر 20MB)\n\n💡 راه حل:\n• از عکس با کیفیت کمتر استفاده کنید\n• فایل را فشرده کنید\n• از ابزارهای آنلاین برای کاهش حجم استفاده کنید")
            return
        
        # دریافت اطلاعات فایل از Telegram
        file_info = requests.get(API + f"getFile?file_id={file_id}").json()
        if not file_info.get("ok"):
            error_desc = file_info.get("description", "خطای نامشخص")
            if "file is too big" in error_desc.lower():
                send_message(chat_id, "❌ فایل خیلی بزرگ است!\n\n💡 راه حل:\n• از عکس با کیفیت کمتر استفاده کنید\n• فایل را فشرده کنید\n• حداکثر حجم مجاز: 20MB")
            else:
                send_message(chat_id, f"❌ خطا در دریافت اطلاعات فایل!\n\n🔍 جزئیات: {error_desc}")
            return
        
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # دانلود فایل با timeout و بررسی حجم
        try:
            response = requests.get(file_url, timeout=30, stream=True)
            if response.status_code != 200:
                send_message(chat_id, f"❌ خطا در دانلود فایل! (کد خطا: {response.status_code})\n\n💡 لطفاً دوباره تلاش کنید یا از فایل کوچکتری استفاده کنید.")
                return
            
            # بررسی حجم واقعی فایل
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 20 * 1024 * 1024:
                send_message(chat_id, "❌ فایل خیلی بزرگ است! (حداکثر 20MB)\n\n💡 راه حل:\n• از عکس با کیفیت کمتر استفاده کنید\n• فایل را فشرده کنید")
                return
            
            # دانلود محتوا
            file_content = response.content
            
        except requests.exceptions.Timeout:
            send_message(chat_id, "⏰ زمان دانلود فایل تمام شد!\n\n💡 راه حل:\n• اینترنت خود را بررسی کنید\n• از فایل کوچکتری استفاده کنید\n• دوباره تلاش کنید")
            return
        except requests.exceptions.RequestException as e:
            send_message(chat_id, f"❌ خطا در دانلود فایل!\n\n🔍 جزئیات: {str(e)[:100]}\n\n💡 لطفاً دوباره تلاش کنید.")
            return
        
        # پردازش بر اساس نوع عملیات
        send_message(chat_id, "⚙️ در حال پردازش...")
        
        if mode == "video_sticker_to_gif":
            result = convert_video_sticker_to_gif(response.content, file_path)
            if result:
                success = send_animation_file(chat_id, result, "✅ استیکر ویدیویی به GIF تبدیل شد!")
                if not success:
                    send_message(chat_id, "❌ خطا در ارسال فایل تبدیل شده!")
            else:
                send_message(chat_id, "❌ خطا در تبدیل فایل! لطفاً مطمئن شوید که فایل معتبر است و FFmpeg نصب شده باشد.")
        
        elif mode == "gif_to_video_sticker":
            result = convert_gif_to_video_sticker(response.content, file_path)
            if result:
                success = send_video_file(chat_id, result, "✅ GIF به استیکر ویدیویی تبدیل شد!")
                if not success:
                    send_message(chat_id, "❌ خطا در ارسال فایل تبدیل شده!")
            else:
                send_message(chat_id, "❌ خطا در تبدیل فایل! لطفاً مطمئن شوید که فایل GIF معتبر است و FFmpeg نصب شده باشد.")
        
        elif mode == "photo_to_sticker":
            result = convert_photo_to_sticker(response.content)
            if result:
                success = send_document_file(chat_id, result, "✅ عکس به استیکر تبدیل شد!")
                if not success:
                    send_message(chat_id, "❌ خطا در ارسال فایل تبدیل شده!")
            else:
                send_message(chat_id, "❌ خطا در تبدیل فایل! لطفاً مطمئن شوید که فایل عکس معتبر است.")
        
        elif mode == "sticker_to_photo":
            result = convert_sticker_to_photo(response.content)
            if result:
                success = send_photo_file(chat_id, result, "✅ استیکر به عکس تبدیل شد!")
                if not success:
                    send_message(chat_id, "❌ خطا در ارسال فایل تبدیل شده!")
            else:
                send_message(chat_id, "❌ خطا در تبدیل فایل! لطفاً مطمئن شوید که استیکر معتبر است.")
        
        elif mode == "png_to_sticker":
            result = convert_png_to_sticker(response.content)
            if result:
                success = send_document_file(chat_id, result, "✅ PNG به استیکر تبدیل شد!")
                if not success:
                    send_message(chat_id, "❌ خطا در ارسال فایل تبدیل شده!")
            else:
                send_message(chat_id, "❌ خطا در تبدیل فایل! لطفاً مطمئن شوید که فایل PNG معتبر است.")
        
        elif mode == "file_to_video":
            result = convert_file_to_video(response.content, file_path)
            if result:
                success = send_video_file(chat_id, result, "✅ فایل به ویدیو تبدیل شد!")
                if not success:
                    send_message(chat_id, "❌ خطا در ارسال فایل تبدیل شده!")
            else:
                send_message(chat_id, "❌ خطا در تبدیل فایل! لطفاً مطمئن شوید که فایل ویدیو معتبر است و FFmpeg نصب شده باشد.")
        
        elif mode == "video_message_to_video":
            result = convert_video_message_to_video(response.content)
            if result:
                success = send_video_file(chat_id, result, "✅ ویدیو مسیج به ویدیو عادی تبدیل شد!")
                if not success:
                    send_message(chat_id, "❌ خطا در ارسال فایل تبدیل شده!")
            else:
                send_message(chat_id, "❌ خطا در تبدیل فایل! لطفاً مطمئن شوید که ویدیو مسیج معتبر است و FFmpeg نصب شده باشد.")
        
        # ریست کردن حالت
        user_data[chat_id]["mode"] = None
        user_data[chat_id]["step"] = None
        save_user_data()
        
    except Exception as e:
        logger.error(f"Error in handle_premium_file: {e}")
        send_message(chat_id, "❌ خطا در پردازش فایل!")

def convert_video_sticker_to_gif(file_content, original_path):
    """تبدیل استیکر ویدیویی به GIF"""
    try:
        # بررسی وجود ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("FFmpeg not found or not working")
            return None
        
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as input_file:
            input_file.write(file_content)
            input_file.flush()
            
            output_path = input_file.name.replace(".webm", ".gif")
            
            # تبدیل با ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", input_file.name,
                "-vf", "fps=10,scale=320:320:flags=lanczos",
                "-c:v", "gif", "-f", "gif",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    gif_content = f.read()
                
                # حذف فایل‌های موقت
                try:
                    os.unlink(input_file.name)
                    os.unlink(output_path)
                except:
                    pass
                
                return gif_content
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                # حذف فایل‌های موقت در صورت خطا
                try:
                    os.unlink(input_file.name)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                except:
                    pass
                return None
                
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return None
    except Exception as e:
        logger.error(f"Error converting video sticker to gif: {e}")
        return None

def convert_gif_to_video_sticker(file_content, original_path):
    """تبدیل GIF به استیکر ویدیویی"""
    try:
        # بررسی وجود ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("FFmpeg not found or not working")
            return None
        
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as input_file:
            input_file.write(file_content)
            input_file.flush()
            
            output_path = input_file.name.replace(".gif", ".webm")
            
            # تبدیل با ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", input_file.name,
                "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                "-vf", "scale=512:512:flags=lanczos",
                "-an", "-f", "webm", "-t", "3",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    webm_content = f.read()
                
                # حذف فایل‌های موقت
                try:
                    os.unlink(input_file.name)
                    os.unlink(output_path)
                except:
                    pass
                
                return webm_content
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                # حذف فایل‌های موقت در صورت خطا
                try:
                    os.unlink(input_file.name)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                except:
                    pass
                return None
                
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return None
    except Exception as e:
        logger.error(f"Error converting gif to video sticker: {e}")
        return None

def convert_photo_to_sticker(file_content):
    """تبدیل عکس به استیکر با بهینه‌سازی برای فایل‌های بزرگ"""
    try:
        # بررسی حجم فایل
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            logger.warning(f"Large image file: {len(file_content)} bytes")
        
        # بارگذاری تصویر با بهینه‌سازی حافظه
        img = Image.open(BytesIO(file_content))
        
        # تبدیل به RGBA با بهینه‌سازی
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # اگر تصویر خیلی بزرگ است، ابتدا آن را کوچک کن
        original_size = img.size
        if original_size[0] > 2048 or original_size[1] > 2048:
            # کاهش اندازه به حداکثر 2048 پیکسل
            img.thumbnail((2048, 2048), Image.LANCZOS)
            logger.info(f"Image resized from {original_size} to {img.size}")
        
        # تغییر اندازه به 512x512
        img = img.resize((512, 512), Image.LANCZOS)
        
        # ذخیره در فرمت WebP با کیفیت بهینه
        output_buffer = BytesIO()
        
        # تنظیم کیفیت بر اساس حجم اصلی
        if len(file_content) > 5 * 1024 * 1024:  # 5MB
            quality = 75
        elif len(file_content) > 2 * 1024 * 1024:  # 2MB
            quality = 85
        else:
            quality = 90
        
        img.save(output_buffer, format="WebP", quality=quality, optimize=True)
        output_buffer.seek(0)
        
        result = output_buffer.getvalue()
        logger.info(f"Sticker created: {len(file_content)} -> {len(result)} bytes")
        
        return result
        
    except MemoryError:
        logger.error("Memory error while processing large image")
        return None
    except Exception as e:
        logger.error(f"Error converting photo to sticker: {e}")
        return None

def convert_png_to_sticker(file_content):
    """تبدیل PNG به استیکر با بهینه‌سازی برای فایل‌های بزرگ"""
    try:
        # بررسی حجم فایل
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            logger.warning(f"Large PNG file: {len(file_content)} bytes")
        
        # بارگذاری تصویر
        img = Image.open(BytesIO(file_content))
        
        # تبدیل به RGBA
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # اگر تصویر خیلی بزرگ است، ابتدا آن را کوچک کن
        original_size = img.size
        if original_size[0] > 2048 or original_size[1] > 2048:
            img.thumbnail((2048, 2048), Image.LANCZOS)
            logger.info(f"PNG resized from {original_size} to {img.size}")
        
        # تغییر اندازه به 512x512
        img = img.resize((512, 512), Image.LANCZOS)
        
        # ذخیره در فرمت WebP
        output_buffer = BytesIO()
        
        # تنظیم کیفیت بر اساس حجم اصلی
        if len(file_content) > 5 * 1024 * 1024:  # 5MB
            quality = 75
        elif len(file_content) > 2 * 1024 * 1024:  # 2MB
            quality = 85
        else:
            quality = 90
        
        img.save(output_buffer, format="WebP", quality=quality, optimize=True)
        output_buffer.seek(0)
        
        result = output_buffer.getvalue()
        logger.info(f"PNG to sticker: {len(file_content)} -> {len(result)} bytes")
        
        return result
        
    except MemoryError:
        logger.error("Memory error while processing large PNG")
        return None
    except Exception as e:
        logger.error(f"Error converting PNG to sticker: {e}")
        return None

def convert_sticker_to_photo(file_content):
    """تبدیل استیکر به عکس"""
    try:
        # بارگذاری تصویر
        img = Image.open(BytesIO(file_content)).convert("RGBA")
        
        # ایجاد پس‌زمینه سفید
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])  # استفاده از کانال آلفا
        
        # ذخیره در فرمت JPEG
        output_buffer = BytesIO()
        background.save(output_buffer, format="JPEG", quality=95)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error converting sticker to photo: {e}")
        return None


def convert_file_to_video(file_content, original_path):
    """تبدیل فایل به ویدیو قابل پخش"""
    try:
        # بررسی وجود ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("FFmpeg not found or not working")
            return None
        
        # تشخیص پسوند فایل
        extension = os.path.splitext(original_path)[1].lower()
        if not extension:
            extension = ".mp4"
        
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as input_file:
            input_file.write(file_content)
            input_file.flush()
            
            output_path = input_file.name.replace(extension, ".mp4")
            
            # تبدیل با ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", input_file.name,
                "-c:v", "libx264", "-c:a", "aac",
                "-preset", "medium", "-crf", "23",
                "-movflags", "+faststart",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    video_content = f.read()
                
                # حذف فایل‌های موقت
                try:
                    os.unlink(input_file.name)
                    os.unlink(output_path)
                except:
                    pass
                
                return video_content
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                # حذف فایل‌های موقت در صورت خطا
                try:
                    os.unlink(input_file.name)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                except:
                    pass
                return None
                
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return None
    except Exception as e:
        logger.error(f"Error converting file to video: {e}")
        return None

def convert_video_message_to_video(file_content):
    """تبدیل ویدیو مسیج به ویدیو عادی"""
    try:
        # بررسی وجود ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            logger.error("FFmpeg not found or not working")
            return None
        
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as input_file:
            input_file.write(file_content)
            input_file.flush()
            
            output_path = input_file.name.replace(".mp4", "_converted.mp4")
            
            # تبدیل با ffmpeg (حذف محدودیت‌های ویدیو مسیج)
            cmd = [
                "ffmpeg", "-y", "-i", input_file.name,
                "-c:v", "libx264", "-c:a", "aac",
                "-preset", "medium", "-crf", "23",
                "-vf", "scale=-2:480",  # کاهش اندازه برای سرعت بیشتر
                "-movflags", "+faststart",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    video_content = f.read()
                
                # حذف فایل‌های موقت
                try:
                    os.unlink(input_file.name)
                    os.unlink(output_path)
                except:
                    pass
                
                return video_content
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                # حذف فایل‌های موقت در صورت خطا
                try:
                    os.unlink(input_file.name)
                    if os.path.exists(output_path):
                        os.unlink(output_path)
                except:
                    pass
                return None
                
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout")
        return None
    except Exception as e:
        logger.error(f"Error converting video message to video: {e}")
        return None

def send_photo_file(chat_id, file_content, caption):
    """ارسال فایل عکس"""
    try:
        files = {"photo": ("photo.jpg", BytesIO(file_content), "image/jpeg")}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(API + "sendPhoto", files=files, data=data)
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error sending photo: {e}")
        return False

def send_video_file(chat_id, file_content, caption):
    """ارسال فایل ویدیو"""
    try:
        files = {"video": ("video.mp4", BytesIO(file_content), "video/mp4")}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(API + "sendVideo", files=files, data=data)
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error sending video: {e}")
        return False

def send_animation_file(chat_id, file_content, caption):
    """ارسال فایل انیمیشن (GIF)"""
    try:
        files = {"animation": ("animation.gif", BytesIO(file_content), "image/gif")}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(API + "sendAnimation", files=files, data=data)
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error sending animation: {e}")
        return False

def send_document_file(chat_id, file_content, caption):
    """ارسال فایل به عنوان Document"""
    try:
        files = {"document": ("sticker.webp", BytesIO(file_content), "image/webp")}
        data = {"chat_id": chat_id, "caption": caption}
        response = requests.post(API + "sendDocument", files=files, data=data)
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error sending document: {e}")
        return False

def process_user_state(chat_id, text):
    """پردازش حالت کاربر - این تابع جداگانه برای پردازش حالت‌ها"""
    state = user_data.get(chat_id, {})
    
    # پردازش بازخورد منفی - درخواست دلیل
    if state.get("step") == "waiting_feedback_reason":
        save_negative_feedback(chat_id, text)
        user_data[chat_id]["step"] = "text"  # بازگشت به حالت عادی
        send_message_with_back_button(chat_id, "🙏 ممنون از بازخوردتون! سعی می‌کنیم بهتر شیم.\n\n✍️ متن استیکر بعدی را بفرست:")
        return True
    
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
            
            # اضافه کردن شناسه کاربر برای جلوگیری از تداخل
            unique_pack_name = f"{pack_name}_{chat_id}_by_{BOT_USERNAME}"
            
            # اگر نام خیلی طولانی شد، کوتاهش کن
            if len(unique_pack_name) > 64:
                # کوتاه کردن نام اصلی
                max_name_length = 64 - len(f"_{chat_id}_by_{BOT_USERNAME}")
                pack_name = pack_name[:max_name_length]
                unique_pack_name = f"{pack_name}_{chat_id}_by_{BOT_USERNAME}"
            
            # اگر نام تبدیل شده با نام اصلی متفاوت بود، به کاربر اطلاع بده
            if pack_name != original_name.replace(" ", "_"):
                send_message(chat_id, f"ℹ️ نام پک شما از '{original_name}' به '{pack_name}' تبدیل شد تا با قوانین تلگرام سازگار باشد.")
            
            # بررسی اینکه پک با این نام وجود دارد یا نه (اگرچه با شناسه کاربر احتمال تداخل کمه)
            resp = requests.get(API + f"getStickerSet?name={unique_pack_name}").json()
            if resp.get("ok"):
                # اگر پک وجود داشت، شماره اضافه کن
                counter = 1
                while True:
                    test_name = f"{pack_name}_{counter}_{chat_id}_by_{BOT_USERNAME}"
                    if len(test_name) <= 64:
                        resp = requests.get(API + f"getStickerSet?name={test_name}").json()
                        if not resp.get("ok"):
                            unique_pack_name = test_name
                            break
                    counter += 1
                    if counter > 100:  # جلوگیری از حلقه بی‌نهایت
                        unique_pack_name = f"pack_{int(time.time())}_{chat_id}_by_{BOT_USERNAME}"
                        break
            
            user_data[chat_id]["pack_name"] = unique_pack_name
            logger.info(f"Pack name set for user {chat_id}: {unique_pack_name}")
            
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
                
                # ارسال پیام با دکمه‌های بازخورد
                send_feedback_message(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد.{limit_info}{settings_info}")
                
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

def show_subscription_menu(chat_id):
    """نمایش منوی اشتراک"""
    if is_subscribed(chat_id):
        # کاربر اشتراک فعال دارد - نمایش قابلیت‌های ویژه
        subscription = subscription_data[chat_id]
        expires_at = subscription.get("expires_at", 0)
        expires_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expires_at))
        
        message = f"""💎 اشتراک فعال ✅

📅 انقضا: {expires_date}
🎉 شما دسترسی به تمام قابلیت‌ها دارید!

🔥 قابلیت‌های ویژه:"""
        
        keyboard = {
            "keyboard": [
                ["🎞 تبدیل استیکر ویدیویی به گیف", "🎥 تبدیل گیف به استیکر ویدیویی"],
                ["🖼 تبدیل عکس به استیکر", "📂 تبدیل استیکر به عکس"],
                ["🌃 تبدیل PNG به استیکر", "🗂 تبدیل فایل ویدیو"],
                ["🎥 تبدیل ویدیو مسیج"],
                ["🔙 بازگشت"]
            ],
            "resize_keyboard": True
        }
        requests.post(API + "sendMessage", json={
            "chat_id": chat_id,
            "text": message,
            "reply_markup": keyboard
        })
    else:
        # نمایش طرح‌های اشتراک
        message = f"""💎 اشتراک نامحدود

🎯 مزایای اشتراک:
• ساخت استیکر متنی نامحدود
• تبدیل استیکر ویدیویی به گیف
• تبدیل گیف به استیکر ویدیویی
• تبدیل عکس به استیکر معمولی
• تبدیل استیکر به عکس و PNG
• تبدیل PNG به عکس و استیکر
• تبدیل فایل ویدیو به ویدیو قابل پخش
• تبدیل ویدیو مسیج به ویدیو معمولی
• پشتیبانی اولویت‌دار

💰 طرح‌های قیمت:"""
        
        keyboard = {
            "keyboard": [
                ["📦 یک ماهه - ۱۰۰ تومان"],
                ["📦 سه ماهه - ۲۵۰ تومان"], 
                ["📦 یک ساله - ۳۵۰ تومان"],
                ["🔙 بازگشت"]
            ],
            "resize_keyboard": True
        }
        requests.post(API + "sendMessage", json={
            "chat_id": chat_id,
            "text": message,
            "reply_markup": keyboard
        })

def show_payment_info(chat_id, plan):
    """نمایش اطلاعات پرداخت برای طرح انتخابی"""
    plan_info = SUBSCRIPTION_PLANS[plan]
    
    # ذخیره طرح انتخابی کاربر
    if chat_id not in user_data:
        user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
    user_data[chat_id]["selected_plan"] = plan
    save_user_data()
    
    message = f"""💳 اطلاعات پرداخت

📦 طرح: {plan_info['title']}
💰 مبلغ: {plan_info['price']} تومان
⏰ مدت: {plan_info['days']} روز

💳 مشخصات کارت:
🏦 شماره کارت: {CARD_NUMBER}
👤 نام صاحب کارت: {CARD_NAME}

📝 مراحل پرداخت:
1️⃣ مبلغ {plan_info['price']} تومان را به کارت بالا واریز کنید
2️⃣ عکس رسید واریز را ارسال کنید
3️⃣ منتظر تایید پشتیبانی باشید

⚠️ توجه: رسید را حتماً ارسال کنید تا اشتراک شما فعال شود.

📞 پشتیبانی: {SUPPORT_ID} - اگر مشکلی پیش آمد، حتماً پیوی بزنید!"""
    
    keyboard = {
        "keyboard": [
            ["📸 ارسال رسید"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": message,
        "reply_markup": keyboard
    })

def handle_admin_command(chat_id, text):
    """پردازش دستورات ادمین"""
    if not is_admin(chat_id):
        send_message(chat_id, "❌ شما دسترسی ادمین ندارید!")
        return True
    
    parts = text.split()
    if len(parts) < 2:
        send_message(chat_id, """🔧 پنل مدیریت ربات

📋 دستورات موجود:
/admin add <user_id> <days>     # فعال کردن اشتراک
/admin remove <user_id>         # قطع اشتراک  
/admin list                     # لیست کاربران اشتراکی
/admin stats                    # آمار کلی ربات
/admin broadcast <message>      # ارسال پیام همگانی
/admin payments                 # رسیدهای در انتظار

💡 مثال: /admin add 123456789 30""")
        return True
    
    command = parts[1].lower()
    
    if command == "add" and len(parts) >= 4:
        try:
            user_id = int(parts[2])
            days = int(parts[3])
            
            current_time = time.time()
            expires_at = current_time + (days * 24 * 3600)
            
            subscription_data[user_id] = {
                "expires_at": expires_at,
                "created_at": current_time,
                "days": days,
                "admin_id": chat_id
            }
            save_subscription_data()
            
            expires_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expires_at))
            send_message(chat_id, f"✅ اشتراک {days} روزه برای کاربر {user_id} فعال شد!\n📅 انقضا: {expires_date}")
            
            # اطلاع به کاربر
            try:
                send_message(user_id, f"🎉 اشتراک شما فعال شد!\n📅 انقضا: {expires_date}\n\n🎯 حالا می‌توانید از تمام قابلیت‌های ربات استفاده کنید!")
            except:
                logger.error(f"Failed to notify user {user_id}")
            
        except ValueError:
            send_message(chat_id, "❌ لطفاً ایدی و تعداد روز را به صورت عدد وارد کنید!")
    
    elif command == "remove" and len(parts) >= 3:
        try:
            user_id = int(parts[2])
            if user_id in subscription_data:
                del subscription_data[user_id]
                save_subscription_data()
                send_message(chat_id, f"✅ اشتراک کاربر {user_id} قطع شد!")
                try:
                    send_message(user_id, "❌ اشتراک شما توسط ادمین قطع شد!")
                except:
                    logger.error(f"Failed to notify user {user_id}")
            else:
                send_message(chat_id, f"❌ کاربر {user_id} اشتراک فعال ندارد!")
        except ValueError:
            send_message(chat_id, "❌ لطفاً ایدی را به صورت عدد وارد کنید!")
    
    elif command == "list":
        if not subscription_data:
            send_message(chat_id, "📋 هیچ کاربر اشتراکی وجود ندارد!")
        else:
            message = "📋 لیست کاربران اشتراکی:\n\n"
            current_time = time.time()
            for user_id, sub in subscription_data.items():
                expires_at = sub.get("expires_at", 0)
                expires_date = time.strftime("%Y-%m-%d", time.localtime(expires_at))
                days = sub.get("days", 0)
                status = "✅ فعال" if current_time < expires_at else "❌ منقضی"
                message += f"👤 {user_id}: {days} روز - {expires_date} ({status})\n"
            send_message(chat_id, message)
    
    elif command == "stats":
        total_users = len(user_data)
        subscribed_users = len(subscription_data)
        active_subscriptions = sum(1 for sub in subscription_data.values() 
                                 if time.time() < sub.get("expires_at", 0))
        
        # محاسبه استیکرهای ساخته شده امروز
        today_stickers = 0
        current_time = time.time()
        today_start = current_time - (current_time % (24 * 3600))
        
        for user in user_data.values():
            usage = user.get("sticker_usage", [])
            today_stickers += sum(1 for timestamp in usage if timestamp >= today_start)
        
        # محاسبه آمار بازخورد
        positive_feedbacks = sum(1 for f in feedback_data.values() if f.get("type") == "positive")
        negative_feedbacks = sum(1 for f in feedback_data.values() if f.get("type") == "negative")
        total_feedbacks = positive_feedbacks + negative_feedbacks
        satisfaction_rate = (positive_feedbacks / total_feedbacks * 100) if total_feedbacks > 0 else 0
        
        message = f"""📊 آمار کلی ربات

👥 کل کاربران: {total_users}
💎 کاربران اشتراکی: {subscribed_users}
✅ اشتراک‌های فعال: {active_subscriptions}
❌ اشتراک‌های منقضی: {subscribed_users - active_subscriptions}

📈 آمار امروز:
🎨 استیکر ساخته شده: {today_stickers}
🔔 رسیدهای در انتظار: {len(pending_payments)}

💭 آمار بازخورد:
👍 بازخورد مثبت: {positive_feedbacks}
👎 بازخورد منفی: {negative_feedbacks}
📊 میزان رضایت: {satisfaction_rate:.1f}%"""
        send_message(chat_id, message)
    
    elif command == "payments":
        if not pending_payments:
            send_message(chat_id, "📋 هیچ رسیدی در انتظار تایید نیست!")
        else:
            message = "📋 رسیدهای در انتظار:\n\n"
            for payment_id, payment in pending_payments.items():
                user_id = payment["user_id"]
                first_name = payment["first_name"]
                username = payment["username"]
                plan = payment["plan"]
                timestamp = payment["timestamp"]
                date = time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
                
                message += f"👤 {first_name} (@{username})\n"
                message += f"🆔 {user_id}\n"
                message += f"📦 {SUBSCRIPTION_PLANS[plan]['title']} - {SUBSCRIPTION_PLANS[plan]['price']} تومان\n"
                message += f"⏰ {date}\n"
                message += f"✅ /admin add {user_id} {SUBSCRIPTION_PLANS[plan]['days']}\n\n"
            
            send_message(chat_id, message)
    
    elif command == "feedback":
        if not feedback_data:
            send_message(chat_id, "💭 هیچ بازخوردی ثبت نشده!")
        else:
            # نمایش آخرین 10 بازخورد
            recent_feedbacks = sorted(feedback_data.items(), key=lambda x: x[1]["timestamp"], reverse=True)[:10]
            message = "💭 آخرین بازخوردها:\n\n"
            
            for feedback_id, feedback in recent_feedbacks:
                user_id = feedback["user_id"]
                feedback_type = "👍 مثبت" if feedback["type"] == "positive" else "👎 منفی"
                timestamp = feedback["timestamp"]
                date = time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
                
                message += f"👤 کاربر: {user_id}\n"
                message += f"💭 نوع: {feedback_type}\n"
                message += f"⏰ زمان: {date}\n"
                
                if feedback.get("reason"):
                    message += f"📝 دلیل: {feedback['reason']}\n"
                
                message += "─────────────\n"
            
            # آمار کلی
            positive_count = sum(1 for f in feedback_data.values() if f.get("type") == "positive")
            negative_count = sum(1 for f in feedback_data.values() if f.get("type") == "negative")
            total_count = positive_count + negative_count
            satisfaction_rate = (positive_count / total_count * 100) if total_count > 0 else 0
            
            message += f"\n📊 آمار کلی:\n"
            message += f"👍 مثبت: {positive_count}\n"
            message += f"👎 منفی: {negative_count}\n"
            message += f"📈 رضایت: {satisfaction_rate:.1f}%"
            
            send_message(chat_id, message)
    
    elif command == "system":
        # بررسی وضعیت سیستم
        system_status = check_system_status()
        send_message(chat_id, system_status)
    
    elif command == "broadcast" and len(parts) >= 3:
        broadcast_message = " ".join(parts[2:])
        success_count = 0
        fail_count = 0
        
        send_message(chat_id, f"📡 شروع ارسال پیام همگانی به {len(user_data)} کاربر...")
        
        for user_id in user_data.keys():
            try:
                send_message(user_id, f"📢 پیام ادمین:\n\n{broadcast_message}")
                success_count += 1
                time.sleep(0.05)  # جلوگیری از محدودیت rate limit
            except:
                fail_count += 1
        
        send_message(chat_id, f"✅ پیام همگانی ارسال شد!\n\n✅ موفق: {success_count}\n❌ ناموفق: {fail_count}")
    
    else:
        send_message(chat_id, "❌ دستور نامعتبر! از /admin help استفاده کنید.")
    
    return True

def is_subscribed(chat_id):
    """بررسی اینکه کاربر اشتراک فعال دارد یا نه"""
    if chat_id not in subscription_data:
        return False
    
    current_time = time.time()
    subscription = subscription_data[chat_id]
    
    # بررسی انقضای اشتراک
    if current_time >= subscription.get("expires_at", 0):
        # اشتراک منقضی شده
        del subscription_data[chat_id]
        save_subscription_data()
        return False
    
    return True

def is_admin(chat_id):
    """بررسی اینکه کاربر ادمین است یا نه"""
    return chat_id == ADMIN_ID

def check_sticker_limit(chat_id):
    """بررسی محدودیت استیکر برای کاربر"""
    # اگر اشتراک فعال دارد، محدودیت ندارد
    if is_subscribed(chat_id):
        return 999, time.time() + 24 * 3600  # نامحدود
    
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
            # اگر فقط یک کلمه است و خیلی بلند است، آن را شکست بده
            w, _ = _measure_text(draw, text, font)
            if w > max_width:
                return _hard_wrap_word(draw, text, font, max_width)
            else:
                return [text]
        
        # برای متن‌های طولانی فارسی، کلمات را کلمه به کلمه در خطوط مختلف قرار بده
        lines = []
        current_line = ""
        
        for word in words:
            # بررسی اینکه آیا کلمه جدید در خط فعلی جا می‌شود یا نه
            test_line = current_line + (" " if current_line else "") + word
            w, _ = _measure_text(draw, test_line, font)
            
            if w <= max_width:
                # کلمه در خط فعلی جا می‌شود
                current_line = test_line
            else:
                # کلمه در خط فعلی جا نمی‌شود
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # اگر خط خالی است و کلمه جا نمی‌شود، باید کلمه را شکست
                    word_parts = _hard_wrap_word(draw, word, font, max_width)
                    lines.extend(word_parts[:-1])
                    current_line = word_parts[-1] if word_parts else ""
        
        # اضافه کردن آخرین خط
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [""]
    
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
    
    logger.info(f"🔍 Getting font: size={size}, language={language}, style={font_style}")
    
    # بررسی وجود پوشه fonts
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(base_dir, "fonts")
    logger.info(f"🔍 Base directory: {base_dir}")
    logger.info(f"🔍 Fonts directory: {fonts_dir}")
    logger.info(f"🔍 Fonts directory exists: {os.path.exists(fonts_dir)}")
    
    if os.path.exists(fonts_dir):
        font_files = os.listdir(fonts_dir)
        logger.info(f"🔍 Available font files: {font_files}")
    
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
        # فونت‌های انگلیسی - اجبار استفاده از Roboto
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # اگر فونت ضخیم انتخاب شده - استفاده از فونت‌های موجود شما
        if "ضخیم" in font_style or "بولد" in font_style:
            font_paths = [
                os.path.join(base_dir, "fonts", "Poppins-Black.ttf"),
                os.path.join(base_dir, "fonts", "Montserrat-VariableFont_wght.ttf"),
                os.path.join(base_dir, "fonts", "Roboto-VariableFont_wdth,wght.ttf"),
                "fonts/Poppins-Black.ttf",
                "fonts/Montserrat-VariableFont_wght.ttf",
                "fonts/Roboto-VariableFont_wdth,wght.ttf"
            ]
        elif "نازک" in font_style or "لایت" in font_style:
            font_paths = [
                os.path.join(base_dir, "fonts", "Roboto-Italic-VariableFont_wdth,wght.ttf"),
                os.path.join(base_dir, "fonts", "OpenSans-VariableFont_wdth,wght.ttf"),
                "fonts/Roboto-Italic-VariableFont_wdth,wght.ttf",
                "fonts/OpenSans-VariableFont_wdth,wght.ttf"
            ]
        else:
            # فونت عادی - استفاده از فونت‌های اصلی شما
            font_paths = [
                os.path.join(base_dir, "fonts", "Roboto-VariableFont_wdth,wght.ttf"),
                os.path.join(base_dir, "fonts", "Montserrat-VariableFont_wght.ttf"),
                os.path.join(base_dir, "fonts", "OpenSans-VariableFont_wdth,wght.ttf"),
                os.path.join(base_dir, "fonts", "Poppins-Black.ttf"),
                "fonts/Roboto-VariableFont_wdth,wght.ttf",
                "fonts/Montserrat-VariableFont_wght.ttf",
                "fonts/OpenSans-VariableFont_wdth,wght.ttf",
                "fonts/Poppins-Black.ttf"
            ]
        
        # اضافه کردن fallback fonts
        font_paths.extend([
            "fonts/arial.ttf",
            "arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Arial.ttf",
            "/Windows/Fonts/arial.ttf",
            "NotoSans-Regular.ttf"
        ])
    
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, size)
            logger.info(f"✅ Successfully loaded font: {font_path} with size: {size} for {language}")
            return font
        except (OSError, IOError) as e:
            logger.warning(f"❌ Failed to load font: {font_path} - {e}")
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
                    path_try = os.path.join(BASE_DIR, template_bg)
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
                    file_size = file_info["result"].get("file_size", 0)
                    
                    # بررسی حجم فایل پس‌زمینه
                    if file_size > 10 * 1024 * 1024:  # 10MB
                        logger.warning(f"Background image too large: {file_size} bytes")
                        # ادامه با پس‌زمینه شفاف
                    else:
                        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                        
                        # دانلود با timeout
                        resp = requests.get(file_url, timeout=15)
                        if resp.status_code == 200:
                            try:
                                bg = Image.open(BytesIO(resp.content))
                                
                                # اگر تصویر خیلی بزرگ است، ابتدا آن را کوچک کن
                                if bg.size[0] > 1024 or bg.size[1] > 1024:
                                    bg.thumbnail((1024, 1024), Image.LANCZOS)
                                    logger.info(f"Background resized to {bg.size}")
                                
                                bg = bg.convert("RGBA")
                                bg = bg.resize((img_size, img_size), Image.LANCZOS)
                                img.paste(bg, (0, 0))
                                background_applied = True
                                logger.info("Background image loaded successfully")
                                
                            except MemoryError:
                                logger.error("Memory error while processing background image")
                            except Exception as img_error:
                                logger.error(f"Error processing background image: {img_error}")
                        else:
                            logger.error(f"Failed to download user background: status={resp.status_code}")
                else:
                    error_desc = file_info.get("description", "خطای نامشخص")
                    if "file is too big" in error_desc.lower():
                        logger.error("Background file too big for Telegram API")
                    else:
                        logger.error(f"getFile not ok for background_file_id: {file_info}")
            except requests.exceptions.Timeout:
                logger.error("Timeout downloading background image")
            except Exception as e:
                logger.error(f"Error loading background: {e}")

        if not background_applied:
            logger.info("No background applied (template/user). Using transparent background.")

        draw = ImageDraw.Draw(img)
        
        # 📌 تنظیمات فونت و باکس متن (بهینه‌سازی برای متن فارسی)
        # تنظیم اندازه فونت از تنظیمات کاربر - اندازه‌های خیلی بزرگتر برای انگلیسی
        if user_settings and "text_size" in user_settings and user_settings["text_size"]:
            size_text = user_settings["text_size"]
            if "خیلی کوچک" in size_text:
                initial_font_size = 70 if language == "english" else 40  # انگلیسی خیلی بزرگتر
            elif "کوچک" in size_text:
                initial_font_size = 95 if language == "english" else 60  # انگلیسی خیلی بزرگتر
            elif "متوسط" in size_text:
                initial_font_size = 120 if language == "english" else 80  # انگلیسی خیلی بزرگتر
            elif "بزرگ" in size_text:
                initial_font_size = 150 if language == "english" else 100  # انگلیسی خیلی بزرگتر
            elif "خیلی بزرگ" in size_text:
                initial_font_size = 180 if language == "english" else 120  # انگلیسی خیلی بزرگتر
            else:
                initial_font_size = 120 if language == "english" else 80  # پیش‌فرض انگلیسی خیلی بزرگتر
        else:
            # اندازه پیش‌فرض خیلی بزرگتر برای انگلیسی
            initial_font_size = 120 if language == "english" else 80
        
        # حداقل اندازه فونت یکسان برای هر دو زبان
        min_font_size = 20
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
        
        # بررسی و کاهش حجم فایل برای استیکر
        file_size = os.path.getsize(path)
        max_attempts = 3
        quality = 90
        
        while file_size > 512 * 1024 and max_attempts > 0:  # حداکثر 512KB
            logger.warning(f"Sticker file too large: {file_size} bytes, compressing with quality {quality}...")
            
            # کاهش کیفیت تدریجی
            if quality > 60:
                quality -= 15
            else:
                # اگر کیفیت خیلی پایین شد، سایز رو کم کن
                final_img = final_img.resize((480, 480), Image.LANCZOS)
                quality = 75
            
            # ذخیره با کیفیت جدید
            final_img.save(path, "PNG", optimize=True, compress_level=9)
            
            # اگر هنوز بزرگ بود، به WebP تبدیل کن
            if os.path.getsize(path) > 512 * 1024:
                webp_path = path.replace('.png', '.webp')
                final_img.save(webp_path, "WebP", quality=quality, optimize=True)
                if os.path.exists(webp_path) and os.path.getsize(webp_path) < os.path.getsize(path):
                    os.remove(path)
                    os.rename(webp_path, path)
            
            file_size = os.path.getsize(path)
            max_attempts -= 1
        
        if file_size > 512 * 1024:
            logger.error(f"Could not compress sticker below 512KB: {file_size} bytes")
            # آخرین تلاش: سایز خیلی کوچک
            final_img = final_img.resize((256, 256), Image.LANCZOS)
            final_img.save(path, "PNG", optimize=True, compress_level=9)
        
        logger.info(f"Sticker saved successfully to {path} with font size: {font_size} for {language}, size: {os.path.getsize(path)} bytes")
        return True
        
    except Exception as e:
        logger.error(f"make_text_sticker error: {e}")
        return False

def show_main_menu(chat_id):
    # بررسی وضعیت اشتراک کاربر
    if is_subscribed(chat_id):
        keyboard = {
            "keyboard": [
                ["🎁 تست رایگان", "⭐ اشتراک"],
                ["🎨 طراحی پیشرفته", "📚 قالب‌های آماده"],
                ["📝 تاریخچه", "⚙️ تنظیمات"],
                ["ℹ️ درباره", "📞 پشتیبانی"]
            ],
            "resize_keyboard": True
        }
    else:
        keyboard = {
            "keyboard": [
                ["🎁 تست رایگان", "⭐ اشتراک"],
                ["🎨 طراحی پیشرفته", "📚 قالب‌های آماده"],
                ["📝 تاریخچه", "⚙️ تنظیمات"],
                ["ℹ️ درباره", "📞 پشتیبانی"]
            ],
            "resize_keyboard": True
        }
    
    welcome_message = tr(chat_id, "main_menu", "👋 خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:")
    
    # اضافه کردن وضعیت اشتراک به پیام
    if is_subscribed(chat_id):
        subscription = subscription_data[chat_id]
        expires_at = subscription.get("expires_at", 0)
        expires_date = time.strftime("%Y-%m-%d", time.localtime(expires_at))
        welcome_message += f"\n\n💎 اشتراک فعال تا: {expires_date}"
    else:
        remaining, _ = check_sticker_limit(chat_id)
        welcome_message += f"\n\n📊 استیکر باقی مانده: {remaining}/5"
    
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": welcome_message,
        "reply_markup": keyboard
    })

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

def show_language_menu(chat_id):
    """نمایش منوی زبان"""
    keyboard = {
        "keyboard": [
            ["🇮🇷 فارسی", "🇺🇸 انگلیسی"],
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
    try:
        bot_username = BOT_USERNAME
        if not bot_username.startswith("@"):
            deep = f"https://t.me/{bot_username}?start={chat_id}"
        else:
            deep = f"https://t.me/{bot_username[1:]}?start={chat_id}"
        send_message_with_back_button(chat_id, f"📤 لینک اشتراک‌گذاری:\n\n🔗 {deep}")
    except Exception as e:
        logger.error(f"Error generating share link: {e}")
        send_message_with_back_button(chat_id, "📤 لینک اشتراک‌گذاری:\n\n🔗 https://t.me/your_bot")

def send_feedback_message(chat_id, message):
    """ارسال پیام با دکمه‌های بازخورد"""
    keyboard = {
        "keyboard": [
            ["👍 عالی بود!", "👎 خوب نبود"],
            ["✍️ متن بعدی", "📷 تغییر بکگراند"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": message + "\n\n💭 نظرتون درباره این استیکر چیه؟",
        "reply_markup": keyboard
    })

def handle_feedback(chat_id, feedback):
    """پردازش بازخورد کاربر"""
    if feedback == "👍 عالی بود!":
        # بازخورد مثبت
        save_positive_feedback(chat_id)
        send_message_with_back_button(chat_id, "🙏 ممنون از نظر مثبتتون! خوشحالیم که راضی هستید.\n\n✍️ متن استیکر بعدی را بفرست:\n\n📷 یا عکس جدید برای تغییر بکگراند بفرست:")
    
    elif feedback == "👎 خوب نبود":
        # بازخورد منفی - درخواست دلیل
        user_data[chat_id]["step"] = "waiting_feedback_reason"
        send_message_with_back_button(chat_id, "😔 متأسفیم که راضی نبودید.\n\n💬 لطفاً بگید چه مشکلی داشت تا بتونیم بهتر شیم:")

def save_positive_feedback(chat_id):
    """ذخیره بازخورد مثبت"""
    feedback_id = f"{chat_id}_{int(time.time())}"
    feedback_data[feedback_id] = {
        "user_id": chat_id,
        "type": "positive",
        "timestamp": time.time(),
        "rating": 5
    }
    save_feedback_data()
    logger.info(f"Positive feedback saved for user {chat_id}")

def save_negative_feedback(chat_id, reason):
    """ذخیره بازخورد منفی با دلیل"""
    feedback_id = f"{chat_id}_{int(time.time())}"
    feedback_data[feedback_id] = {
        "user_id": chat_id,
        "type": "negative",
        "timestamp": time.time(),
        "rating": 2,
        "reason": reason
    }
    save_feedback_data()
    logger.info(f"Negative feedback saved for user {chat_id}: {reason}")

def check_system_status():
    """بررسی وضعیت سیستم و ابزارهای مورد نیاز"""
    status_message = "🔧 وضعیت سیستم:\n\n"
    
    # بررسی FFmpeg
    ffmpeg_status = "❌ نصب نشده"
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # استخراج نسخه FFmpeg
            version_line = result.stdout.split('\n')[0]
            ffmpeg_status = f"✅ نصب شده - {version_line}"
        else:
            ffmpeg_status = "❌ خطا در اجرا"
    except subprocess.TimeoutExpired:
        ffmpeg_status = "⏰ timeout"
    except FileNotFoundError:
        ffmpeg_status = "❌ نصب نشده"
    except Exception as e:
        ffmpeg_status = f"❌ خطا: {str(e)[:50]}"
    
    status_message += f"🎬 FFmpeg: {ffmpeg_status}\n\n"
    
    # بررسی PIL/Pillow
    pil_status = "✅ نصب شده"
    try:
        from PIL import Image
        pil_version = Image.__version__ if hasattr(Image, '__version__') else "نامشخص"
        pil_status = f"✅ نصب شده - v{pil_version}"
    except ImportError:
        pil_status = "❌ نصب نشده"
    except Exception as e:
        pil_status = f"❌ خطا: {str(e)[:50]}"
    
    status_message += f"🖼️ PIL/Pillow: {pil_status}\n\n"
    
    # بررسی فونت‌های فارسی
    persian_fonts = [
        "fonts/Vazirmatn-Regular.ttf",
        "fonts/IRANSans.ttf",
        "fonts/Vazir.ttf"
    ]
    
    found_fonts = []
    for font_path in persian_fonts:
        try:
            full_path = os.path.join(BASE_DIR, font_path)
            if os.path.exists(full_path):
                found_fonts.append(font_path)
        except:
            pass
    
    if found_fonts:
        status_message += f"📝 فونت‌های فارسی: ✅ {len(found_fonts)} فونت موجود\n"
        for font in found_fonts[:3]:  # نمایش حداکثر 3 فونت
            status_message += f"   • {font}\n"
    else:
        status_message += "📝 فونت‌های فارسی: ❌ هیچ فونت فارسی پیدا نشد\n"
    
    status_message += "\n"
    
    # بررسی فایل‌های داده
    data_files = [
        ("user_data.json", DATA_FILE),
        ("subscriptions.json", SUBSCRIPTION_FILE),
        ("pending_payments.json", PAYMENTS_FILE),
        ("feedback_data.json", FEEDBACK_FILE)
    ]
    
    status_message += "💾 فایل‌های داده:\n"
    for name, path in data_files:
        if os.path.exists(path):
            size = os.path.getsize(path)
            status_message += f"   • {name}: ✅ ({size} bytes)\n"
        else:
            status_message += f"   • {name}: ❌ وجود ندارد\n"
    
    status_message += "\n"
    
    # بررسی متغیرهای محیطی
    env_vars = [
        ("BOT_TOKEN", "✅ تنظیم شده" if BOT_TOKEN else "❌ تنظیم نشده"),
        ("APP_URL", "✅ تنظیم شده" if APP_URL else "❌ تنظیم نشده"),
        ("BOT_USERNAME", "✅ تنظیم شده" if BOT_USERNAME else "❌ تنظیم نشده")
    ]
    
    status_message += "🔧 متغیرهای محیطی:\n"
    for var_name, status in env_vars:
        status_message += f"   • {var_name}: {status}\n"
    
    return status_message

def get_file_size_error_message(file_size_bytes, file_type="فایل"):
    """ایجاد پیام خطای مناسب برای فایل‌های بزرگ"""
    size_mb = file_size_bytes / (1024 * 1024)
    
    message = f"❌ {file_type} خیلی بزرگ است! ({size_mb:.1f}MB)\n\n"
    message += "💡 راه‌های حل:\n"
    
    if file_type == "عکس":
        message += "• از تنظیمات دوربین، کیفیت عکس را کاهش دهید\n"
        message += "• از اپلیکیشن‌های فشرده‌سازی عکس استفاده کنید\n"
        message += "• عکس را در اندازه کوچکتر ذخیره کنید\n"
        message += "• از فرمت JPEG به جای PNG استفاده کنید\n"
    else:
        message += "• فایل را فشرده کنید\n"
        message += "• از ابزارهای آنلاین برای کاهش حجم استفاده کنید\n"
        message += "• فایل را در کیفیت کمتر ذخیره کنید\n"
    
    message += f"\n📏 حداکثر حجم مجاز: 20MB\n"
    message += f"📊 حجم فعلی شما: {size_mb:.1f}MB"
    
    return message

def handle_file_processing_error(chat_id, error_type, details=""):
    """مدیریت خطاهای پردازش فایل و ارائه راه‌حل"""
    if error_type == "memory_error":
        message = "❌ فایل خیلی بزرگ است و حافظه کافی نیست!\n\n"
        message += "💡 راه‌های حل:\n"
        message += "• از عکس با کیفیت کمتر استفاده کنید\n"
        message += "• عکس را فشرده کنید\n"
        message += "• چند دقیقه صبر کنید و دوباره تلاش کنید\n"
        message += "• از عکس با اندازه کوچکتر استفاده کنید"
        
    elif error_type == "timeout":
        message = "⏰ زمان پردازش فایل تمام شد!\n\n"
        message += "💡 راه‌های حل:\n"
        message += "• اتصال اینترنت خود را بررسی کنید\n"
        message += "• از فایل کوچکتری استفاده کنید\n"
        message += "• چند لحظه صبر کنید و دوباره تلاش کنید\n"
        message += "• در زمان‌های کم‌ترافیک تلاش کنید"
        
    elif error_type == "invalid_format":
        message = "❌ فرمت فایل پشتیبانی نمی‌شود!\n\n"
        message += "💡 راه‌های حل:\n"
        message += "• از فرمت‌های معتبر استفاده کنید (JPG, PNG, WebP)\n"
        message += "• فایل را در فرمت دیگری ذخیره کنید\n"
        message += "• مطمئن شوید فایل خراب نیست"
        
    elif error_type == "download_failed":
        message = "❌ خطا در دانلود فایل!\n\n"
        message += "💡 راه‌های حل:\n"
        message += "• اتصال اینترنت خود را بررسی کنید\n"
        message += "• دوباره فایل را ارسال کنید\n"
        message += "• از فایل کوچکتری استفاده کنید\n"
        message += "• چند لحظه صبر کنید و تلاش کنید"
        
    else:
        message = f"❌ خطا در پردازش فایل!\n\n"
        if details:
            message += f"🔍 جزئیات: {details[:100]}\n\n"
        message += "💡 راه‌های حل:\n"
        message += "• دوباره تلاش کنید\n"
        message += "• از فایل دیگری استفاده کنید\n"
        message += "• با پشتیبانی تماس بگیرید"
    
    send_message_with_back_button(chat_id, message)

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
