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

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bot")

# Basic config
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set!")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret").strip()
APP_URL = os.environ.get("APP_URL")
if APP_URL:
    APP_URL = APP_URL.strip().rstrip('/')

BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "@YourChannel")
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# Admin and payment config
ADMIN_ID = 6053579919
SUPPORT_ID = "@onedaytoalive"
CARD_NUMBER = os.environ.get("CARD_NUMBER", "1234-5678-9012-3456")
CARD_NAME = os.environ.get("CARD_NAME", "نام شما")

# Data storage
user_data = {}
subscription_data = {}
pending_payments = {}
feedback_data = {}

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "user_data.json")
SUBSCRIPTION_FILE = os.path.join(BASE_DIR, "subscriptions.json")
PAYMENTS_FILE = os.path.join(BASE_DIR, "pending_payments.json")
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback_data.json")

# Subscription plans
SUBSCRIPTION_PLANS = {
    "1month": {"price": 100, "days": 30, "title": "یک ماهه"},
    "3months": {"price": 250, "days": 90, "title": "سه ماهه"},
    "12months": {"price": 350, "days": 365, "title": "یک ساله"}
}

# Localization
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

def get_lang(chat_id):
    return user_data.get(chat_id, {}).get("lang", "fa")

def tr(chat_id, key, fallback_text):
    lang = get_lang(chat_id)
    return LOCALES.get(lang, {}).get(key, fallback_text)

# Data management functions
def load_data():
    """Load all data files"""
    global user_data, subscription_data, pending_payments, feedback_data
    
    def load_json_file(filename, default_data):
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default_data
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return default_data
    
    user_data = load_json_file(DATA_FILE, {})
    subscription_data = load_json_file(SUBSCRIPTION_FILE, {})
    pending_payments = load_json_file(PAYMENTS_FILE, {})
    feedback_data = load_json_file(FEEDBACK_FILE, {})
    
    logger.info(f"Data loaded: {len(user_data)} users, {len(subscription_data)} subscriptions")

def save_data():
    """Save all data files"""
    def save_json_file(data, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")
            return False
    
    save_json_file(user_data, DATA_FILE)
    save_json_file(subscription_data, SUBSCRIPTION_FILE)
    save_json_file(pending_payments, PAYMENTS_FILE)
    save_json_file(feedback_data, FEEDBACK_FILE)

# Flask app
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is running!"

@app.route("/health")
def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=['POST'])
def webhook():
    """Main webhook endpoint"""
    try:
        data = request.get_json(force=True)
        if not data:
            return "No data", 400
        
        logger.info(f"Received update: {data}")
        
        # Handle callback queries first
        if "callback_query" in data:
            callback_query = data["callback_query"]
            handle_callback_query(callback_query)
            return "OK"
        
        # Handle messages
        if "message" in data:
            message = data["message"]
            chat_id = message.get("chat", {}).get("id")
            if chat_id:
                process_message(message)
            return "OK"
        
        return "OK"
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

# Utility functions
def send_message(chat_id, text, reply_markup=None):
    """Send message to user"""
    try:
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        response = requests.post(API + "sendMessage", json=data, timeout=10)
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def answer_callback_query(query_id, text=None, show_alert=False):
    """Answer callback query"""
    try:
        data = {"callback_query_id": query_id}
        if text:
            data["text"] = text
        if show_alert:
            data["show_alert"] = show_alert
        
        response = requests.post(API + "answerCallbackQuery", json=data, timeout=5)
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error answering callback: {e}")
        return False

def edit_message_text(chat_id, message_id, text, reply_markup=None):
    """Edit message text"""
    try:
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        response = requests.post(API + "editMessageText", json=data, timeout=5)
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return False

def is_subscribed(chat_id):
    """Check if user has active subscription"""
    if chat_id not in subscription_data:
        return False
    
    current_time = time.time()
    subscription = subscription_data[chat_id]
    
    if current_time >= subscription.get("expires_at", 0):
        del subscription_data[chat_id]
        save_data()
        return False
    
    return True

def is_admin(chat_id):
    """Check if user is admin"""
    return chat_id == ADMIN_ID

def check_sticker_limit(chat_id):
    """Check sticker limit for user"""
    if is_subscribed(chat_id):
        return 999, time.time() + 24 * 3600  # Unlimited
    
    if chat_id not in user_data:
        return 5, time.time() + 24 * 3600
    
    current_time = time.time()
    user_info = user_data[chat_id]
    
    last_reset = user_info.get("last_reset", current_time)
    next_reset = last_reset + 24 * 3600
    
    if current_time >= next_reset:
        user_info["sticker_usage"] = []
        user_info["last_reset"] = current_time
        save_data()
    
    used_stickers = len(user_info.get("sticker_usage", []))
    remaining = 5 - used_stickers
    
    return max(0, remaining), next_reset

def record_sticker_usage(chat_id):
    """Record sticker usage"""
    if chat_id not in user_data:
        user_data[chat_id] = {
            "mode": None, "count": 0, "step": None, "pack_name": None,
            "background": None, "created_packs": [], "sticker_usage": [],
            "last_reset": time.time()
        }
    
    current_time = time.time()
    user_info = user_data[chat_id]
    
    last_reset = user_info.get("last_reset", current_time)
    next_reset = last_reset + 24 * 3600
    
    if current_time >= next_reset:
        user_info["sticker_usage"] = []
        user_info["last_reset"] = current_time
    
    user_info["sticker_usage"].append(current_time)
    save_data()

def check_channel_membership(chat_id):
    """Check if user is member of required channel"""
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
        }, timeout=5).json()
        
        if response.get("ok"):
            status = response["result"]["status"]
            return status in ["member", "administrator", "creator"]
        
        return False
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

def send_membership_required_message(chat_id):
    """Send membership required message"""
    message = f"""🔒 عضویت در کانال اجباری است!

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
    
    send_message(chat_id, message, json.dumps(keyboard))

# Message processing
def process_message(msg):
    """Process incoming messages"""
    try:
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id:
            return
        
        # Initialize user data if needed
        if chat_id not in user_data:
            user_data[chat_id] = {
                "mode": None, "count": 0, "step": None, "pack_name": None,
                "background": None, "created_packs": [], "sticker_usage": [],
                "last_reset": time.time()
            }
            save_data()
        
        # Process text messages
        if "text" in msg:
            text = msg["text"]
            
            # Handle /start command
            if text == "/start":
                if not check_channel_membership(chat_id):
                    send_membership_required_message(chat_id)
                    return
                
                # Reset user to main menu
                user_data[chat_id].update({
                    "mode": None, "step": None, "background": None
                })
                save_data()
                show_main_menu(chat_id)
                return
            
            # Handle admin commands
            if text.startswith("/admin") and is_admin(chat_id):
                handle_admin_command(chat_id, text)
                return
            
            # Check channel membership for regular messages
            if not check_channel_membership(chat_id):
                send_membership_required_message(chat_id)
                return
            
            # Process user state
            if process_user_state(chat_id, text):
                return
            
            # Handle menu buttons
            handle_menu_buttons(chat_id, text)
        
        # Process photos
        if "photo" in msg:
            handle_photo(chat_id, msg["photo"])
        
        # Process stickers, videos, etc.
        if any(key in msg for key in ["sticker", "video", "animation", "video_note", "document"]):
            handle_premium_file(chat_id, msg)
    
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        send_message(chat_id, "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

def handle_callback_query(callback_query):
    """Handle callback queries"""
    try:
        query_id = callback_query.get('id')
        chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
        message_id = callback_query.get('message', {}).get('message_id')
        data = callback_query.get('data', '')
        
        # Answer callback query immediately
        answer_callback_query(query_id, "در حال پردازش...")
        
        logger.info(f"Processing callback: {data} from chat: {chat_id}")
        
        # Handle different callback types
        if data == "back_to_main":
            edit_message_text(chat_id, message_id, "✅ بازگشت به منوی اصلی")
            show_main_menu(chat_id)
        
        elif data == "new_sticker":
            if chat_id in user_data:
                user_data[chat_id]["step"] = "text"
                save_data()
            send_message(chat_id, "لطفاً متن مورد نظر خود را برای تبدیل به استیکر وارد کنید:")
        
        elif data == 'lang_fa':
            set_language(chat_id, 'fa')
            edit_message_text(chat_id, message_id, tr(chat_id, "lang_set_fa", "✅ زبان به فارسی تغییر کرد."))
            show_main_menu(chat_id)
        
        elif data == 'lang_en':
            set_language(chat_id, 'en')
            edit_message_text(chat_id, message_id, tr(chat_id, "lang_set_en", "✅ Language set to English."))
            show_main_menu(chat_id)
        
        elif data.startswith('sub_'):
            plan = data.replace('sub_', '')
            if plan in SUBSCRIPTION_PLANS:
                start_subscription_process(chat_id, plan)
        
        else:
            logger.warning(f"Unknown callback: {data}")
    
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        if 'query_id' in locals():
            answer_callback_query(query_id, "خطا در پردازش", True)

def handle_menu_buttons(chat_id, text):
    """Handle menu button presses"""
    try:
        if text == "🎁 تست رایگان":
            handle_free_test(chat_id)
        
        elif text == "⭐ اشتراک":
            show_subscription_menu(chat_id)
        
        elif text == "🎨 طراحی پیشرفته":
            show_advanced_design_menu(chat_id)
        
        elif text == "📚 قالب‌های آماده":
            show_template_menu(chat_id)
        
        elif text == "📝 تاریخچه":
            show_history(chat_id)
        
        elif text == "⚙️ تنظیمات":
            show_settings_menu(chat_id)
        
        elif text == "📞 پشتیبانی":
            send_message(chat_id, f"📞 برای پشتیبانی با {SUPPORT_ID} در تماس باشید.\n\nاگر مشکلی پیش آمد، حتماً پیوی بزنید!")
        
        elif text == "ℹ️ درباره":
            send_message(chat_id, "ℹ️ این ربات برای ساخت استیکر متنی است. نسخه فعلی رایگان است.")
        
        elif text == "🔙 بازگشت":
            if chat_id in user_data:
                user_data[chat_id].update({"mode": None, "step": None})
                save_data()
            show_main_menu(chat_id)
        
        else:
            # Default response
            send_message(chat_id, "❓ دستور شناخته شده نیست. لطفاً از منو استفاده کنید.")
    
    except Exception as e:
        logger.error(f"Error handling menu button: {e}")
        send_message(chat_id, "⚠️ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

def process_user_state(chat_id, text):
    """Process user state based on current step"""
    try:
        state = user_data.get(chat_id, {})
        step = state.get("step")
        
        if step == "text":
            # User wants to create a sticker
            remaining, next_reset = check_sticker_limit(chat_id)
            if remaining <= 0:
                next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                send_message(chat_id, f"⏰ محدودیت روزانه شما تمام شده!\n\n🔄 زمان بعدی: {next_reset_time}")
                return True
            
            # Create sticker
            success = create_text_sticker(chat_id, text)
            if success:
                user_data[chat_id]["count"] += 1
                record_sticker_usage(chat_id)
                send_feedback_message(chat_id, f"✅ استیکر شماره {user_data[chat_id]['count']} ساخته شد!")
            else:
                send_message(chat_id, "❌ خطا در ساخت استیکر")
            return True
        
        elif step == "pack_name":
            # User is setting pack name
            pack_name = sanitize_pack_name(text)
            unique_pack_name = f"{pack_name}_{chat_id}_by_{BOT_USERNAME}"
            
            user_data[chat_id]["pack_name"] = unique_pack_name
            user_data[chat_id]["step"] = "background"
            save_data()
            
            send_message(chat_id, "📷 یک عکس برای بکگراند استیکر خود ارسال کنید:")
            return True
        
        elif step == "background":
            # User should send a photo, not text
            send_message(chat_id, "📷 لطفاً یک عکس برای بکگراند ارسال کنید، نه متن.")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error processing user state: {e}")
        return False

def handle_free_test(chat_id):
    """Handle free test button"""
    try:
        remaining, next_reset = check_sticker_limit(chat_id)
        if remaining <= 0:
            next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
            send_message(chat_id, f"⏰ محدودیت روزانه شما تمام شده!\n\n🔄 زمان بعدی: {next_reset_time}")
            return
        
        # Initialize user for free test
        if not user_data[chat_id].get("pack_name"):
            user_data[chat_id]["step"] = "pack_name"
            save_data()
            send_message(chat_id, "📝 لطفاً یک نام برای پک استیکر خود انتخاب کنید:")
        else:
            user_data[chat_id]["step"] = "text"
            save_data()
            send_message(chat_id, "✍️ متن استیکر خود را بفرستید:")
    
    except Exception as e:
        logger.error(f"Error in free test: {e}")

def handle_photo(chat_id, photos):
    """Handle photo messages"""
    try:
        state = user_data.get(chat_id, {})
        step = state.get("step")
        
        if step == "background":
            # User is setting background
            photo = photos[-1]  # Get highest quality
            file_id = photo.get("file_id")
            
            if file_id:
                user_data[chat_id]["background"] = file_id
                user_data[chat_id]["step"] = "text"
                save_data()
                send_message(chat_id, "✅ بکگراند تنظیم شد!\n\n✍️ حالا متن استیکر خود را بفرستید:")
        
        elif step == "waiting_receipt":
            # User is sending payment receipt
            handle_payment_receipt(chat_id, photos[-1]["file_id"])
    
    except Exception as e:
        logger.error(f"Error handling photo: {e}")

def handle_premium_file(chat_id, msg):
    """Handle premium file processing"""
    try:
        if not is_subscribed(chat_id):
            send_message(chat_id, "⭐ این قابلیت فقط برای کاربران اشتراکی است!")
            return
        
        # Process different file types
        # This is a placeholder - implement actual file processing
        send_message(chat_id, "⚙️ در حال پردازش فایل...")
        time.sleep(1)  # Simulate processing
        send_message(chat_id, "✅ فایل پردازش شد!")
    
    except Exception as e:
        logger.error(f"Error handling premium file: {e}")

# Sticker creation functions
def sanitize_pack_name(text):
    """Convert pack name to acceptable format"""
    import unicodedata
    
    sanitized = ""
    for char in text:
        if char.isalnum() and ord(char) < 128:
            sanitized += char
        elif char.isspace():
            sanitized += "_"
        else:
            sanitized += "x"
    
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    
    if not sanitized or len(sanitized) < 2:
        sanitized = "pack"
    
    return sanitized[:50]  # Limit length

def create_text_sticker(chat_id, text):
    """Create text sticker"""
    try:
        sticker_path = "sticker.png"
        
        # Create simple text sticker
        if not make_simple_sticker(text, sticker_path):
            return False
        
        pack_name = user_data[chat_id].get("pack_name")
        if not pack_name:
            return False
        
        # Get user info
        user_info = requests.get(API + f"getChat?chat_id={chat_id}").json()
        first_name = user_info.get("result", {}).get("first_name", "User")
        pack_title = f"{first_name}'s Stickers"
        
        # Check if pack exists
        resp = requests.get(API + f"getStickerSet?name={pack_name}").json()
        
        if not resp.get("ok"):
            # Create new pack
            with open(sticker_path, "rb") as f:
                files = {"png_sticker": f}
                data = {
                    "user_id": chat_id,
                    "name": pack_name,
                    "title": pack_title,
                    "emojis": "🔥"
                }
                r = requests.post(API + "createNewStickerSet", data=data, files=files)
                if not r.json().get("ok"):
                    return False
        else:
            # Add to existing pack
            with open(sticker_path, "rb") as f:
                files = {"png_sticker": f}
                data = {
                    "user_id": chat_id,
                    "name": pack_name,
                    "emojis": "🔥"
                }
                r = requests.post(API + "addStickerToSet", data=data, files=files)
                if not r.json().get("ok"):
                    return False
        
        # Send sticker to user
        time.sleep(1)
        final = requests.get(API + f"getStickerSet?name={pack_name}").json()
        if final.get("ok"):
            stickers = final["result"]["stickers"]
            if stickers:
                file_id = stickers[-1]["file_id"]
                send_resp = requests.post(API + "sendSticker", data={"chat_id": chat_id, "sticker": file_id})
                return send_resp.json().get("ok", False)
        
        return False
    
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        return False

def make_simple_sticker(text, path):
    """Create a simple text sticker"""
    try:
        # Create 512x512 image
        img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))  # Transparent background
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        font_size = 48
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Calculate text size and position
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width = len(text) * 20
            text_height = 40
        
        # Center text
        x = (512 - text_width) // 2
        y = (512 - text_height) // 2
        
        # Draw text with outline
        outline_width = 2
        for dx in [-outline_width, 0, outline_width]:
            for dy in [-outline_width, 0, outline_width]:
                if dx != 0 or dy != 0:
                    if font:
                        draw.text((x + dx, y + dy), text, font=font, fill="white")
                    else:
                        draw.text((x + dx, y + dy), text, fill="white")
        
        # Draw main text
        if font:
            draw.text((x, y), text, font=font, fill="black")
        else:
            draw.text((x, y), text, fill="black")
        
        # Save
        img.save(path, "PNG")
        return True
    
    except Exception as e:
        logger.error(f"Error making sticker: {e}")
        return False

# UI Functions
def show_main_menu(chat_id):
    """Show main menu"""
    try:
        remaining, _ = check_sticker_limit(chat_id)
        subscription_status = ""
        
        if is_subscribed(chat_id):
            subscription = subscription_data[chat_id]
            expires_date = time.strftime("%Y-%m-%d", time.localtime(subscription.get("expires_at", 0)))
            subscription_status = f"\n\n💎 اشتراک فعال تا: {expires_date}"
        else:
            subscription_status = f"\n\n📊 استیکر رایگان: {remaining}/5"
        
        keyboard = {
            "keyboard": [
                ["🎁 تست رایگان", "⭐ اشتراک"],
                ["🎨 طراحی پیشرفته", "📚 قالب‌های آماده"],
                ["📝 تاریخچه", "⚙️ تنظیمات"],
                ["📞 پشتیبانی", "ℹ️ درباره"]
            ],
            "resize_keyboard": True
        }
        
        message = tr(chat_id, "main_menu", "👋 خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:") + subscription_status
        send_message(chat_id, message, json.dumps(keyboard))
    
    except Exception as e:
        logger.error(f"Error showing main menu: {e}")

def send_feedback_message(chat_id, message):
    """Send message with feedback buttons"""
    keyboard = {
        "keyboard": [
            ["👍 عالی بود!", "👎 خوب نبود"],
            ["✍️ متن بعدی"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    
    full_message = message + "\n\n💭 نظرتان درباره این استیکر چیست؟"
    send_message(chat_id, full_message, json.dumps(keyboard))

def show_subscription_menu(chat_id):
    """Show subscription menu"""
    if is_subscribed(chat_id):
        subscription = subscription_data[chat_id]
        expires_date = time.strftime("%Y-%m-%d", time.localtime(subscription.get("expires_at", 0)))
        message = f"💎 اشتراک فعال ✅\n\n📅 انقضا: {expires_date}"
        
        keyboard = {
            "keyboard": [["🔙 بازگشت"]],
            "resize_keyboard": True
        }
    else:
        message = """💎 اشتراک نامحدود

🎯 مزایای اشتراک:
• ساخت استیکر نامحدود
• قابلیت‌های ویژه
• پشتیبانی اولویت‌دار

💰 طرح‌های قیمت:"""
        
        keyboard = {
            "inline_keyboard": [
                [{"text": f"📦 {SUBSCRIPTION_PLANS['1month']['title']} - {SUBSCRIPTION_PLANS['1month']['price']} تومان", "callback_data": "sub_1month"}],
                [{"text": f"📦 {SUBSCRIPTION_PLANS['3months']['title']} - {SUBSCRIPTION_PLANS['3months']['price']} تومان", "callback_data": "sub_3months"}],
                [{"text": f"📦 {SUBSCRIPTION_PLANS['12months']['title']} - {SUBSCRIPTION_PLANS['12months']['price']} تومان", "callback_data": "sub_12months"}]
            ]
        }
    
    send_message(chat_id, message, json.dumps(keyboard))

def start_subscription_process(chat_id, plan):
    """Start subscription process"""
    try:
        plan_info = SUBSCRIPTION_PLANS[plan]
        user_data[chat_id]["selected_plan"] = plan
        save_data()
        
        message = f"""💳 اطلاعات پرداخت

📦 طرح: {plan_info['title']}
💰 مبلغ: {plan_info['price']} تومان
⏰ مدت: {plan_info['days']} روز

💳 مشخصات کارت:
🏦 شماره کارت: {CARD_NUMBER}
👤 نام صاحب کارت: {CARD_NAME}

📝 مراحل پرداخت:
1️⃣ مبلغ {plan_info['price']} تومان را واریز کنید
2️⃣ عکس رسید را ارسال کنید
3️⃣ منتظر تایید باشید"""
        
        keyboard = {
            "keyboard": [
                ["📸 ارسال رسید"],
                ["🔙 بازگشت"]
            ],
            "resize_keyboard": True
        }
        
        send_message(chat_id, message, json.dumps(keyboard))
    
    except Exception as e:
        logger.error(f"Error starting subscription: {e}")

def set_language(chat_id, lang):
    """Set user language"""
    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]["lang"] = lang
    save_data()

def show_advanced_design_menu(chat_id):
    """Show advanced design menu"""
    keyboard = {
        "keyboard": [
            ["🎨 رنگ‌ها", "📝 فونت‌ها"],
            ["📏 اندازه‌ها", "✨ افکت‌ها"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "🎨 طراحی پیشرفته:\n\nانتخاب کنید:", json.dumps(keyboard))

def show_template_menu(chat_id):
    """Show template menu"""
    keyboard = {
        "keyboard": [
            ["🎉 تولد", "💒 عروسی"],
            ["🎊 جشن", "💝 عاشقانه"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "📚 قالب‌های آماده:\n\nانتخاب کنید:", json.dumps(keyboard))

def show_history(chat_id):
    """Show user history"""
    packs = user_data.get(chat_id, {}).get("created_packs", [])
    if not packs:
        message = "📝 شما هنوز استیکری نساخته‌اید."
    else:
        message = "📝 تاریخچه استیکرها:\n\n"
        for i, pack in enumerate(packs[:5], 1):  # Show max 5
            message += f"{i}. {pack.get('title', 'بدون نام')}\n"
    
    keyboard = {
        "keyboard": [["🔙 بازگشت"]],
        "resize_keyboard": True
    }
    send_message(chat_id, message, json.dumps(keyboard))

def show_settings_menu(chat_id):
    """Show settings menu"""
    keyboard = {
        "keyboard": [
            ["🌍 زبان"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "⚙️ تنظیمات:", json.dumps(keyboard))

def handle_payment_receipt(chat_id, file_id):
    """Handle payment receipt"""
    try:
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
            "plan": user_data.get(chat_id, {}).get("selected_plan", "1month")
        }
        save_data()
        
        # Notify admin
        admin_message = f"""🔔 رسید جدید!

👤 {first_name} (@{username})
🆔 {chat_id}
📦 {SUBSCRIPTION_PLANS[pending_payments[payment_id]['plan']]['title']}
💰 {SUBSCRIPTION_PLANS[pending_payments[payment_id]['plan']]['price']} تومان

/admin add {chat_id} {SUBSCRIPTION_PLANS[pending_payments[payment_id]['plan']]['days']}"""
        
        requests.post(API + "sendPhoto", data={
            "chat_id": ADMIN_ID,
            "photo": file_id,
            "caption": admin_message
        })
        
        user_data[chat_id]["step"] = None
        save_data()
        send_message(chat_id, "✅ رسید دریافت شد! منتظر تایید باشید.")
    
    except Exception as e:
        logger.error(f"Error handling receipt: {e}")

def handle_admin_command(chat_id, text):
    """Handle admin commands"""
    try:
        parts = text.split()
        if len(parts) < 2:
            send_message(chat_id, """🔧 دستورات ادمین:

/admin add <user_id> <days> - فعال کردن اشتراک
/admin remove <user_id> - قطع اشتراک
/admin list - لیست کاربران
/admin stats - آمار""")
            return
        
        command = parts[1].lower()
        
        if command == "add" and len(parts) >= 4:
            user_id = int(parts[2])
            days = int(parts[3])
            
            expires_at = time.time() + (days * 24 * 3600)
            subscription_data[user_id] = {
                "expires_at": expires_at,
                "created_at": time.time(),
                "days": days
            }
            save_data()
            
            expires_date = time.strftime("%Y-%m-%d", time.localtime(expires_at))
            send_message(chat_id, f"✅ اشتراک {days} روزه برای {user_id} فعال شد!\nانقضا: {expires_date}")
            
            # Notify user
            try:
                send_message(user_id, f"🎉 اشتراک فعال شد!\nانقضا: {expires_date}")
            except:
                pass
        
        elif command == "remove" and len(parts) >= 3:
            user_id = int(parts[2])
            if user_id in subscription_data:
                del subscription_data[user_id]
                save_data()
                send_message(chat_id, f"✅ اشتراک {user_id} قطع شد!")
                try:
                    send_message(user_id, "❌ اشتراک شما قطع شد!")
                except:
                    pass
            else:
                send_message(chat_id, f"❌ کاربر {user_id} اشتراک ندارد!")
        
        elif command == "list":
            if not subscription_data:
                send_message(chat_id, "📋 هیچ کاربر اشتراکی وجود ندارد!")
            else:
                message = "📋 کاربران اشتراکی:\n\n"
                for user_id, sub in list(subscription_data.items())[:10]:  # Max 10
                    expires_date = time.strftime("%Y-%m-%d", time.localtime(sub.get("expires_at", 0)))
                    status = "✅" if time.time() < sub.get("expires_at", 0) else "❌"
                    message += f"{user_id}: {expires_date} {status}\n"
                send_message(chat_id, message)
        
        elif command == "stats":
            total_users = len(user_data)
            total_subs = len(subscription_data)
            active_subs = sum(1 for sub in subscription_data.values()
                            if time.time() < sub.get("expires_at", 0))
            
            message = f"""📊 آمار:
👥 کل کاربران: {total_users}
💎 اشتراک‌ها: {total_subs}
✅ فعال: {active_subs}
❌ منقضی: {total_subs - active_subs}"""
            
            send_message(chat_id, message)
    
    except Exception as e:
        logger.error(f"Error in admin command: {e}")
        send_message(chat_id, "❌ خطا در اجرای دستور!")

# Initialize and run
if __name__ == "__main__":
    # Load data
    load_data()
    
    # Register webhook
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        try:
            data = {
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"]
            }
            resp = requests.post(f"{API}setWebhook", json=data, timeout=10)
            result = resp.json()
            
            if result.get("ok"):
                logger.info(f"✅ Webhook registered: {webhook_url}")
            else:
                logger.error(f"❌ Webhook registration failed: {result}")
        
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
    
    # Start server
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting bot on port {port}")
    
    try:
        serve(app, host="0.0.0.0", port=port, threads=4)
    except Exception as e:
        logger.error(f"Server error: {e}")
