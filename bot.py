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
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "@YourChannel")
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# دیتابیس ساده در حافظه
user_data = {}
DATA_FILE = "user_data.json"

def load_user_data():
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
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved user data: {len(user_data)} users")
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

load_user_data()
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is running!"
    def process_user_state(chat_id, text):
    """پردازش حالت کاربر"""
    state = user_data.get(chat_id, {})
    
    if state.get("mode") == "free":
        step = state.get("step")
        
        if step == "ask_pack_choice":
            if text == "1":
                send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:\n\n💡 می‌تونید فارسی، انگلیسی یا حتی ایموجی بنویسید، ربات خودش تبدیلش می‌کنه!")
                user_data[chat_id]["step"] = "pack_name"
            elif text == "2":
                created_packs = user_data[chat_id].get("created_packs", [])
                if created_packs:
                    pack_list = ""
                    for i, pack in enumerate(created_packs, 1):
                        pack_list += f"{i}. {pack['title']}\n"
                    send_message(chat_id, f"�� پک‌های موجود شما:\n{pack_list}\nلطفاً شماره پک مورد نظر را انتخاب کنید:")
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
            original_name = text
            pack_name = sanitize_pack_name(text)
            full_pack_name = f"{pack_name}_by_{BOT_USERNAME}"
            
            if pack_name != original_name.replace(" ", "_"):
                send_message(chat_id, f"ℹ️ نام پک شما از '{original_name}' به '{pack_name}' تبدیل شد تا با قوانین تلگرام سازگار باشد.")
            
            resp = requests.get(API + f"getStickerSet?name={full_pack_name}").json()
            if resp.get("ok"):
                send_message(chat_id, f"❌ پک با نام '{pack_name}' از قبل وجود دارد. لطفاً نام دیگری انتخاب کنید:")
                return True
            
            user_data[chat_id]["pack_name"] = full_pack_name
            send_message_with_back_button(chat_id, "📷 یک عکس برای بکگراند استیکرت بفرست:")
            user_data[chat_id]["step"] = "background"
            return True

        if step == "text":
            remaining, next_reset = check_sticker_limit(chat_id)
            if remaining <= 0:
                next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                send_message(chat_id, f"⏰ محدودیت روزانه شما تمام شده!\n\n🔄 زمان بعدی: {next_reset_time}\n\n💎 برای ساخت استیکر نامحدود، اشتراک تهیه کنید.")
                return True
            
            text_sticker = text
            send_message(chat_id, "⚙️ در حال ساخت استیکر...")
            background_file_id = user_data[chat_id].get("background")
            
            pack_name = user_data[chat_id].get("pack_name")
            logger.info(f"Creating sticker for pack: {pack_name}")
            
            success = send_as_sticker(chat_id, text_sticker, background_file_id)
            
            if success:
                user_data[chat_id]["count"] += 1
                record_sticker_usage(chat_id)
                
                remaining, next_reset = check_sticker_limit(chat_id)
                next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                limit_info = f"\n📊 وضعیت: {remaining}/5 استیکر باقی مانده\n🔄 زمان بعدی: {next_reset_time}"
                
                settings_info = ""
                if user_data[chat_id].get("text_color"):
                    settings_info += f"\n🎨 رنگ: {user_data[chat_id]['text_color']}"
                if user_data[chat_id].get("font_style"):
                    settings_info += f"\n📝 فونت: {user_data[chat_id]['font_style']}"
                if user_data[chat_id].get("text_size"):
                    settings_info += f"\n�� اندازه: {user_data[chat_id]['text_size']}"
                
                send_message_with_back_button(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد.{limit_info}{settings_info}\n\n✍️ متن استیکر بعدی را بفرست:\n\n📷 یا عکس جدید برای تغییر بکگراند بفرست:")
            return True
    
    elif state.get("mode") == "advanced_design":
        step = state.get("step")
        
        if step in ["color_selection", "font_selection", "size_selection", "position_selection", "background_color_selection", "effect_selection"]:
            user_data[chat_id]["mode"] = "free"
            user_data[chat_id]["step"] = "text"
            if not user_data[chat_id].get("pack_name"):
                user_data[chat_id]["step"] = "pack_name"
                send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کن:\n\n💡 می‌تونید فارسی، انگلیسی یا حتی ایموجی بنویسید، ربات خودش تبدیلش می‌کنه!")
            else:
                send_message_with_back_button(chat_id, "✍️ حالا متن استیکرت رو بفرست:")
            return True
    
    return False
    @app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    msg = update.get("message")

    if not msg:
        return "ok"

    chat_id = msg["chat"]["id"]

    if "text" in msg:
        text = msg["text"]

        # ابتدا پردازش حالت کاربر را بررسی کن
        if process_user_state(chat_id, text):
            return "ok"

        if text == "/start":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            
            if chat_id in user_data:
                old_data = user_data[chat_id]
                user_data[chat_id] = {
                    "mode": None, 
                    "count": 0, 
                    "step": None, 
                    "pack_name": None, 
                    "background": None, 
                    "created_packs": [],
                    "sticker_usage": old_data.get("sticker_usage", []),
                    "last_reset": old_data.get("last_reset", time.time())
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
                if "created_packs" not in user_data[chat_id]:
                    user_data[chat_id]["created_packs"] = []
                if "sticker_usage" not in user_data[chat_id]:
                    user_data[chat_id]["sticker_usage"] = []
                if "last_reset" not in user_data[chat_id]:
                    user_data[chat_id]["last_reset"] = time.time()
            
            remaining, next_reset = check_sticker_limit(chat_id)
            if remaining <= 0:
                next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                send_message(chat_id, f"⏰ محدودیت روزانه شما تمام شده!\n\n🔄 زمان بعدی: {next_reset_time}\n\n💎 برای ساخت استیکر نامحدود، اشتراک تهیه کنید.")
                return "ok"
            
            user_data[chat_id]["mode"] = "free"
            if not user_data[chat_id].get("pack_name"):
                user_data[chat_id]["count"] = 0
                user_data[chat_id]["step"] = "ask_pack_choice"
                user_data[chat_id]["pack_name"] = None
                user_data[chat_id]["background"] = None
            else:
                user_data[chat_id]["step"] = "text"
            
            next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
            limit_info = f"📊 وضعیت شما: {remaining}/5 استیکر باقی مانده\n🔄 زمان بعدی: {next_reset_time}\n\n"
            
            created_packs = user_data[chat_id].get("created_packs", [])
            if user_data[chat_id].get("pack_name"):
                pack_name = user_data[chat_id]["pack_name"]
                send_message_with_back_button(chat_id, limit_info + f"✅ ادامه ساخت استیکر در پک فعلی\n✍️ متن استیکر بعدی را بفرست:\n\n📷 یا عکس جدید برای تغییر بکگراند بفرست:")
            elif created_packs:
                send_message(chat_id, limit_info + "📝 آیا می‌خواهید پک جدید بسازید یا به پک قبلی اضافه کنید؟\n1. ساخت پک جدید\n2. اضافه کردن به پک قبلی")
            else:
                send_message(chat_id, limit_info + "📝 شما هنوز پکی ندارید. لطفاً یک نام برای پک استیکر خود انتخاب کن:\n\n💡 می‌تونید فارسی، انگلیسی یا حتی ایموجی بنویسید، ربات خودش تبدیلش می‌کنه!")
                user_data[chat_id]["step"] = "pack_name"
            return "ok"
                    if text == "🔙 بازگشت":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            
            if chat_id in user_data:
                current_mode = user_data[chat_id].get("mode")
                current_step = user_data[chat_id].get("step")
                
                if current_mode == "advanced_design":
                    if current_step in ["color_selection", "font_selection", "size_selection", "position_selection", "background_color_selection", "effect_selection"]:
                        show_advanced_design_menu(chat_id)
                        return "ok"
                
                elif current_mode == "free" and current_step == "text":
                    user_data[chat_id]["mode"] = None
                    user_data[chat_id]["step"] = None
                    show_main_menu(chat_id)
                    return "ok"
                
                else:
                    user_data[chat_id]["mode"] = None
                    user_data[chat_id]["step"] = None
                    user_data[chat_id]["pack_name"] = None
                    user_data[chat_id]["background"] = None
                    show_main_menu(chat_id)
                    return "ok"
            else:
                show_main_menu(chat_id)
                return "ok"

        if text == "🎨 انتخاب رنگ متن":
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
                    if text in ["�� تولد", "💒 عروسی", "🎊 جشن", "�� عاشقانه", "😄 خنده‌دار", "🔥 هیجان‌انگیز", "📚 آموزشی", "💼 کاری", "🏠 خانوادگی"]:
            apply_template(chat_id, text)
            return "ok"

        if text == "🌙 حالت تاریک":
            set_dark_mode(chat_id, True)
            return "ok"
        elif text == "☀️ حالت روشن":
            set_dark_mode(chat_id, False)
            return "ok"
        elif text == "🔔 اعلان‌ها":
            toggle_notifications(chat_id)
            return "ok"
        elif text == "�� زبان":
            show_language_menu(chat_id)
            return "ok"
        elif text == "💾 ذخیره قالب":
            save_template(chat_id)
            return "ok"
        elif text == "📤 اشتراک‌گذاری":
            share_sticker(chat_id)
            return "ok"

        if text == "🎨 طراحی پیشرفته":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_advanced_design_menu(chat_id)
            return "ok"
        elif text == "📚 قالب‌های آماده":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_template_menu(chat_id)
            return "ok"
        elif text == "📝 تاریخچه":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_history(chat_id)
            return "ok"
        elif text == "⚙️ تنظیمات":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            show_settings_menu(chat_id)
            return "ok"
        elif text == "⭐ اشتراک":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            send_message(chat_id, "💳 بخش اشتراک بعداً فعال خواهد شد.")
        elif text == "ℹ️ درباره":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            send_message(chat_id, "ℹ️ این ربات برای ساخت استیکر متنی است. نسخه فعلی رایگان است.")
        elif text == "📞 پشتیبانی":
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return "ok"
            support_id = os.environ.get("SUPPORT_ID", "@YourSupportID")
            send_message(chat_id, f"�� برای پشتیبانی با {support_id} در تماس باش.")
                    if text in ["�� قرمز", "�� آبی", "�� سبز", "⚫ مشکی", "⚪ سفید", "�� زرد", "🟣 بنفش", "�� نارنجی", "🟤 قهوه‌ای"]:
            color_map = {
                "🔴 قرمز": "#FF0000", "�� آبی": "#0000FF", "🟢 سبز": "#00FF00",
                "⚫ مشکی": "#000000", "⚪ سفید": "#FFFFFF", "🟡 زرد": "#FFFF00",
                "🟣 بنفش": "#800080", "🟠 نارنجی": "#FFA500", "�� قهوه‌ای": "#A52A2A"
            }
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["text_color"] = color_map.get(text, "#000000")
            user_data[chat_id]["mode"] = "free"
            user_data[chat_id]["step"] = "text"
            send_message_with_back_button(chat_id, f"✅ رنگ متن به {text} تغییر کرد!\n\nحالا متن خود را بفرستید:")
            return "ok"

        if text in ["📝 فونت عادی", "📝 فونت ضخیم", "📝 فونت نازک", "�� فونت کج", "📝 فونت فانتزی", "📝 فونت کلاسیک"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["font_style"] = text
            user_data[chat_id]["mode"] = "free"
            user_data[chat_id]["step"] = "text"
            send_message_with_back_button(chat_id, f"✅ فونت به {text} تغییر کرد!\n\nحالا متن خود را بفرستید:")
            return "ok"

        if text in ["�� کوچک", "�� متوسط", "📏 بزرگ", "📏 خیلی کوچک", "📏 خیلی بزرگ"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["text_size"] = text
            user_data[chat_id]["mode"] = "free"
            user_data[chat_id]["step"] = "text"
            send_message_with_back_button(chat_id, f"✅ اندازه متن به {text} تغییر کرد!\n\nحالا متن خود را بفرستید:")
            return "ok"

        if text in ["�� بالا", "📍 وسط", "�� پایین", "📍 راست", "�� چپ", "📍 وسط‌چین"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["text_position"] = text
            user_data[chat_id]["mode"] = "free"
            user_data[chat_id]["step"] = "text"
            send_message_with_back_button(chat_id, f"✅ موقعیت متن به {text} تغییر کرد!\n\nحالا متن خود را بفرستید:")
            return "ok"

        if text in ["🖼️ شفاف", "🖼️ سفید", "��️ مشکی", "��️ آبی", "��️ قرمز", "🖼️ سبز", "🖼️ گرادیانت", "🖼️ الگو"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["background_style"] = text
            user_data[chat_id]["mode"] = "free"
            user_data[chat_id]["step"] = "text"
            send_message_with_back_button(chat_id, f"✅ رنگ پس‌زمینه به {text} تغییر کرد!\n\nحالا متن خود را بفرستید:")
            return "ok"

        if text in ["✨ سایه", "✨ نور", "✨ براق", "✨ مات", "✨ شفاف", "✨ انعکاس", "✨ چرخش", "✨ موج", "✨ پرش"]:
            if chat_id not in user_data:
                user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
            user_data[chat_id]["text_effect"] = text
            user_data[chat_id]["mode"] = "free"
            user_data[chat_id]["step"] = "text"
            send_message_with_back_button(chat_id, f"✅ افکت متن به {text} تغییر کرد!\n\nحالا متن خود را بفرستید:")
            return "ok"

    elif "photo" in msg:
        state = user_data.get(chat_id, {})
        if state.get("mode") == "free":
            photos = msg.get("photo", [])
            if photos:
                file_id = photos[-1].get("file_id")
                if file_id:
                    if state.get("step") == "background":
                        user_data[chat_id]["background"] = file_id
                        user_data[chat_id]["step"] = "text"
                        send_message_with_back_button(chat_id, "✍️ حالا متن استیکرت رو بفرست:")
                    elif state.get("step") == "text":
                        user_data[chat_id]["background"] = file_id
                        send_message_with_back_button(chat_id, "✅ بکگراند تغییر کرد!\n✍️ متن استیکر بعدی را بفرست:")

    return "ok"
    def send_as_sticker(chat_id, text, background_file_id=None):
    sticker_path = "sticker.png"
    
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
        
    user_info = requests.get(API + f"getChat?chat_id={chat_id}").json()
    username = user_info.get("result", {}).get("username", f"user_{chat_id}")
    first_name = user_info.get("result", {}).get("first_name", "User")
    
    pack_title = f"{first_name}'s Stickers"

    resp = requests.get(API + f"getStickerSet?name={pack_name}").json()
    sticker_created = False

    if not resp.get("ok"):
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
                if "created_packs" not in user_data[chat_id]:
                    user_data[chat_id]["created_packs"] = []
                
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
                    save_user_data()
            else:
                send_message(chat_id, f"❌ خطا در ساخت پک: {r.json().get('description', 'خطای نامشخص')}")
                return False
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
            if r.json().get("ok"):
                sticker_created = True
            else:
                send_message(chat_id, f"❌ خطا در اضافه کردن استیکر: {r.json().get('description', 'خطای نامشخص')}")
                return False

    if sticker_created:
        try:
            time.sleep(1)
            
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
    try:
        reshaped = arabic_reshaper.reshape(text)
        return reshaped[::-1]
    except Exception as e:
        logger.error(f"Error reshaping text: {e}")
        return text

def sanitize_pack_name(text):
    import unicodedata
    
    sanitized = ""
    for char in text:
        if char.isalnum() and ord(char) < 128:
            sanitized += char
        elif char.isspace():
            sanitized += "_"
        elif '\u0600' <= char <= '\u06FF':
            persian_to_english = {
                'ا': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's', 'ج': 'j', 'چ': 'ch',
                'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z', 'ر': 'r', 'ز': 'z', 'ژ': 'zh',
                'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a',
                'غ': 'gh', 'ف': 'f', 'ق': 'gh', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm',
                'ن': 'n', 'و': 'v', 'ه': 'h', 'ی': 'y', 'ئ': 'e', 'ء': 'a'
            }
            sanitized += persian_to_english.get(char, 'x')
        elif (ord(char) >= 0x1F600 and ord(char) <= 0x1F64F) or \
             (ord(char) >= 0x1F300 and ord(char) <= 0x1F5FF) or \
             (ord(char) >= 0x1F680 and ord(char) <= 0x1F6FF) or \
             (ord(char) >= 0x1F1E0 and ord(char) <= 0x1F1FF) or \
             (ord(char) >= 0x2600 and ord(char) <= 0x26FF) or \
             (ord(char) >= 0x2700 and ord(char) <= 0x27BF) or \
             (ord(char) >= 0xFE00 and ord(char) <= 0xFE0F) or \
             (ord(char) >= 0x1F900 and ord(char) <= 0x1F9FF) or \
             (ord(char) >= 0x1F018 and ord(char) <= 0x1F270):
            continue
        else:
            sanitized += "x"
    
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = sanitized.strip('_')
    
    if not sanitized or len(sanitized) < 2:
        sanitized = "pack"
    
    if len(sanitized) > 64:
        sanitized = sanitized[:64]
    
    return sanitized
    def show_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["�� تست رایگان", "⭐ اشتراک"],
            ["🎨 طراحی پیشرفته", "�� قالب‌های آماده"],
            ["📝 تاریخچه", "⚙️ تنظیمات"],
            ["ℹ️ درباره", "�� پشتیبانی"]
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

def send_message_with_back_button(chat_id, text):
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

def check_sticker_limit(chat_id):
    if chat_id not in user_data:
        return 5, time.time() + 24 * 3600
    
    current_time = time.time()
    user_info = user_data[chat_id]
    
    last_reset = user_info.get("last_reset", current_time)
    next_reset = last_reset + 24 * 3600
    
    if current_time >= next_reset:
        user_info["sticker_usage"] = []
        user_info["last_reset"] = current_time
        next_reset = current_time + 24 * 3600
        save_user_data()
        logger.info(f"Reset limit for user {chat_id} at {current_time}")
    
    used_stickers = len(user_info.get("sticker_usage", []))
    remaining = 5 - used_stickers
    
    return max(0, remaining), next_reset

def record_sticker_usage(chat_id):
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
    
    last_reset = user_info.get("last_reset", current_time)
    next_reset = last_reset + 24 * 3600
    
    if current_time >= next_reset:
        user_info["sticker_usage"] = []
        user_info["last_reset"] = current_time
        logger.info(f"Reset limit for user {chat_id} at {current_time}")
    
    user_info["sticker_usage"].append(current_time)
    save_user_data()

def check_channel_membership(chat_id):
    try:
        if CHANNEL_LINK.startswith("@"):
            channel_username = CHANNEL_LINK[1:]
        elif "t.me/" in CHANNEL_LINK:
            channel_username = CHANNEL_LINK.split("t.me/")[-1]
            if channel_username.startswith("@"):
                channel_username = channel_username[1:]
        else:
            channel_username = CHANNEL_LINK
        
        response = requests.get(API + f"getChatMember", params={
            "chat_id": f"@{channel_username}",
            "user_id": chat_id
        }).json()
        
        if response.get("ok"):
            status = response["result"]["status"]
            return status in ["member", "administrator", "creator"]
        else:
            logger.error(f"Error checking membership: {response}")
            return False
            
    except Exception as e:
        logger.error(f"Error in check_channel_membership: {e}")
        return False

def send_membership_required_message(chat_id):
    message = f"""�� عضویت در کانال اجباری است!

برای استفاده از ربات، ابتدا باید عضو کانال ما شوید:

📢 {CHANNEL_LINK}

بعد از عضویت، دوباره /start را بزنید."""
    
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
    """شکستن متن به خطوط متعدد با در نظر گرفتن فاصله‌ها و کلمات خیلی بلند."""
    if not text:
        return [""]
    
    if is_rtl:
        w, _ = _measure_text(draw, text, font)
        if w <= max_width:
            return [text]
        
        words = text.split()
        if len(words) == 1:
            return [text]
        
        lines = []
        for word in words:
            lines.append(word)
        
        return lines[::-1] if lines else [""]
    
    tokens = re.split(r"(\s+)", text)
    lines = []
    current = ""
    for token in tokens:
        if token.strip() == "":
            tentative = current + token
            w, _ = _measure_text(draw, tentative, font)
            if w <= max_width:
                current = tentative
            else:
                if current:
                    lines.append(current.rstrip())
                    current = ""
            continue
        
        tentative = current + token
        w, _ = _measure_text(draw, tentative, font)
        if w <= max_width:
            current = tentative
        else:
            if current:
                lines.append(current.rstrip())
                current = ""
            
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
    persian_arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    persian_arabic_chars = len(persian_arabic_pattern.findall(text))
    
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
            "NotoColorEmoji.ttf",
            "NotoEmoji.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Windows/Fonts/arial.ttf"
        ]
    else:
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

def make_text_sticker(text, path, background_file_id=None, user_settings=None):
    try:
        logger.info(f"Creating sticker with text: {text}")
        
        language = detect_language(text)
        logger.info(f"Detected language: {language}")
        
        if language == "persian_arabic":
            text = reshape_text(text)
        
        img_size = 256
        img = Image.new("RGBA", (img_size, img_size), (255, 255, 255, 0))

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
        
        if language == "persian_arabic":
            initial_font_size = 50
            min_font_size = 12
        else:
            initial_font_size = 440
            min_font_size = 120
        max_width = 110
        max_height = 110
            
        font = get_font(initial_font_size, language)
        
        if font is None:
            logger.error("No font could be loaded, using basic text rendering")
            font = ImageFont.load_default()

        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except:
            try:
                w, h = draw.textsize(text, font=font)
            except:
                w, h = len(text) * (initial_font_size // 20), initial_font_size // 2

        font_size = initial_font_size
        
        while True:
            line_spacing = max(int(font_size * 0.15), 4)
            wrapped_lines = wrap_text_multiline(draw, text, font, max_width, is_rtl=(language=="persian_arabic"))
            block_w, block_h = measure_multiline_block(draw, wrapped_lines, font, line_spacing)
            if (block_w <= max_width and block_h <= max_height):
                lines = wrapped_lines
                break
            if font_size <= min_font_size:
                lines = wrapped_lines
                break
            font_size -= 3
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
        
        if language == "persian_arabic":
            line_spacing = max(int(font_size * 0.1), 2)
        else:
            line_spacing = max(int(font_size * 0.15), 3)
        lines = wrap_text_multiline(draw, text, font, max_width, is_rtl=(language=="persian_arabic"))
        block_w, block_h = measure_multiline_block(draw, lines, font, line_spacing)
        x = (img_size - block_w) / 2
        is_rtl = (language == "persian_arabic")
        y = (img_size - block_h) / 2

        if language == "persian_arabic":
            outline_thickness = 2
        else:
            outline_thickness = 1
        
        text_color = "#000000"
        if user_settings and "text_color" in user_settings:
            text_color = user_settings["text_color"]
        
        current_y = y
        for line in lines:
            w_line, h_line = _measure_text(draw, line, font)
            line_x = x + (block_w - w_line) / 2
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
            try:
                draw.text((line_x, current_y), line, fill=text_color, font=font)
            except Exception as e:
                logger.error(f"Error drawing line: {e}")
                draw.text((line_x, current_y), line, fill=text_color)
            current_y += h_line + line_spacing

        final_img = img.resize((512, 512), Image.LANCZOS)

        final_img.save(path, "PNG", optimize=True, compress_level=9)
        
        file_size = os.path.getsize(path)
        if file_size > 512 * 1024:
            logger.warning(f"Sticker file too large: {file_size} bytes, compressing...")
            final_img.save(path, "PNG", optimize=True, compress_level=9, quality=85)
        
        logger.info(f"Sticker saved successfully to {path} with font size: {font_size} for {language}, size: {os.path.getsize(path)} bytes")
        return True
        
    except Exception as e:
        logger.error(f"make_text_sticker error: {e}")
        return False
    })
    def show_advanced_design_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["�� انتخاب رنگ متن", "📝 انتخاب فونت"],
            ["📏 اندازه متن", "📍 موقعیت متن"],
            ["��️ رنگ پس‌زمینه", "✨ افکت‌های ویژه"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "�� منوی طراحی پیشرفته:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def show_color_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["�� قرمز", "🔵 آبی", "�� سبز"],
            ["⚫ مشکی", "⚪ سفید", "�� زرد"],
            ["🟣 بنفش", "�� نارنجی", "🟤 قهوه‌ای"],
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
    keyboard = {
        "keyboard": [
            ["�� کوچک", "📏 متوسط", "📏 بزرگ"],
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
    keyboard = {
        "keyboard": [
            ["�� بالا", "📍 وسط", "📍 پایین"],
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
    keyboard = {
        "keyboard": [
            ["🖼️ شفاف", "🖼️ سفید", "🖼️ مشکی"],
            ["��️ آبی", "🖼️ قرمز", "🖼️ سبز"],
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

def show_template_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["�� تولد", "💒 عروسی", "�� جشن"],
            ["�� عاشقانه", "😄 خنده‌دار", "🔥 هیجان‌انگیز"],
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
    if chat_id not in user_data or not user_data[chat_id].get("created_packs"):
        send_message_with_back_button(chat_id, "📝 شما هنوز استیکری نساخته‌اید.")
        return
    
    packs = user_data[chat_id]["created_packs"]
    message = "📝 تاریخچه استیکرهای شما:\n\n"
    
    for i, pack in enumerate(packs, 1):
        message += f"{i}. {pack['title']}\n"
    
    send_message_with_back_button(chat_id, message)

def show_settings_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🌙 حالت تاریک", "☀️ حالت روشن"],
            ["🔔 اعلان‌ها", "🌍 زبان"],
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

def apply_template(chat_id, template_name):
    templates = {
        "🎉 تولد": {"color": "#FFFF00", "bg": "🖼️ شفاف", "font": "📝 فونت فانتزی", "size": "📏 بزرگ"},
        "💒 عروسی": {"color": "#FFFFFF", "bg": "🖼️ سفید", "font": "📝 فونت کلاسیک", "size": "�� متوسط"},
        "�� جشن": {"color": "#800080", "bg": "🖼️ شفاف", "font": "📝 فونت ضخیم", "size": "📏 بزرگ"},
        "💝 عاشقانه": {"color": "#FF0000", "bg": "🖼️ شفاف", "font": "📝 فونت کج", "size": "�� متوسط"},
        "�� خنده‌دار": {"color": "#FFA500", "bg": "🖼️ شفاف", "font": "📝 فونت فانتزی", "size": "📏 بزرگ"},
        "🔥 هیجان‌انگیز": {"color": "#FF0000", "bg": "🖼️ شفاف", "font": "📝 فونت ضخیم", "size": "📏 خیلی بزرگ"},
        "�� آموزشی": {"color": "#0000FF", "bg": "🖼️ سفید", "font": "📝 فونت عادی", "size": "�� متوسط"},
        "💼 کاری": {"color": "#000000", "bg": "🖼️ سفید", "font": "📝 فونت کلاسیک", "size": "�� متوسط"},
        "�� خانوادگی": {"color": "#00FF00", "bg": "🖼️ شفاف", "font": "📝 فونت عادی", "size": "📏 متوسط"}
    }
    
    if template_name in templates:
        template = templates[template_name]
        
        if chat_id not in user_data:
            user_data[chat_id] = {"mode": None, "count": 0, "step": None, "pack_name": None, "background": None, "created_packs": [], "sticker_usage": [], "last_reset": time.time()}
        
        user_data[chat_id]["text_color"] = template["color"]
        user_data[chat_id]["background_style"] = template["bg"]
        user_data[chat_id]["font_style"] = template["font"]
        user_data[chat_id]["text_size"] = template["size"]
        user_data[chat_id]["text_position"] = "📍 وسط"
        user_data[chat_id]["text_effect"] = "✨ سایه"
        
        send_message_with_back_button(chat_id, f"✅ قالب '{template_name}' اعمال شد!\n\n🎨 رنگ: {template['color']}\n🖼️ پس‌زمینه: {template['bg']}\n📝 فونت: {template['font']}\n📏 اندازه: {template['size']}\n\nحالا متن خود را بفرستید:")
    else:
        send_message_with_back_button(chat_id, "❌ قالب پیدا نشد!")

def set_dark_mode(chat_id, is_dark):
    mode = "تاریک" if is_dark else "روشن"
    send_message_with_back_button(chat_id, f"✅ حالت {mode} فعال شد!")

def toggle_notifications(chat_id):
    send_message_with_back_button(chat_id, "✅ وضعیت اعلان‌ها تغییر کرد!")

def show_language_menu(chat_id):
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
        "text": "🌍 انتخاب زبان:\n\nانتخاب کنید:",
        "reply_markup": keyboard
    })

def save_template(chat_id):
    send_message_with_back_button(chat_id, "✅ قالب ذخیره شد!")

def share_sticker(chat_id):
    send_message_with_back_button(chat_id, "📤 لینک اشتراک‌گذاری:\n\n🔗 https://t.me/your_bot")

if __name__ == "__main__":
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        resp = requests.get(API + f"setWebhook?url={webhook_url}")
        logger.info(f"setWebhook: {resp.json()}")
    else:
        logger.warning("⚠️ APP_URL is not set. Webhook not registered.")

    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
