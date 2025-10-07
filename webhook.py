import os
import logging
import json
import time
import re
import tempfile
import requests
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")

# تنظیمات
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret").strip()
BOT_USERNAME = os.environ.get("BOT_USERNAME", "MyBot")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "@YourChannel")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6053579919"))
SUPPORT_ID = os.environ.get("SUPPORT_ID", "@onedaytoalive")

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# داده‌های موقت (در محیط واقعی از دیتابیس استفاده کنید)
user_data = {}
subscription_data = {}

def send_message(chat_id, text, reply_markup=None):
    """ارسال پیام به کاربر"""
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    
    try:
        response = requests.post(API + "sendMessage", json=data, timeout=10)
        return response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
        return False

def is_subscribed(chat_id):
    """بررسی اشتراک کاربر"""
    if chat_id not in subscription_data:
        return False
    
    current_time = time.time()
    subscription = subscription_data[chat_id]
    
    if current_time >= subscription.get("expires_at", 0):
        del subscription_data[chat_id]
        return False
    
    return True

def check_sticker_limit(chat_id):
    """بررسی محدودیت استیکر"""
    if is_subscribed(chat_id):
        return 999, time.time() + 24 * 3600
    
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
    
    used_stickers = len(user_info.get("sticker_usage", []))
    remaining = 5 - used_stickers
    
    return max(0, remaining), next_reset

def record_sticker_usage(chat_id):
    """ثبت استفاده از استیکر"""
    if chat_id not in user_data:
        user_data[chat_id] = {
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
    
    user_info["sticker_usage"].append(current_time)

def reshape_text(text):
    """اصلاح متن فارسی/عربی"""
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped)
        return bidi_text
    except Exception as e:
        logger.error(f"Error reshaping text: {e}")
        return text

def detect_language(text):
    """تشخیص زبان متن"""
    if not text or not text.strip():
        return "english"
    
    persian_arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u200C-\u200F]')
    persian_arabic_chars = len(persian_arabic_pattern.findall(text))
    
    english_pattern = re.compile(r'[a-zA-Z]')
    english_chars = len(english_pattern.findall(text))
    
    total_chars = len(text.strip())
    
    if persian_arabic_chars > 0 and (persian_arabic_chars / total_chars) > 0.3:
        return "persian_arabic"
    elif english_chars > 0 and (english_chars / total_chars) > 0.5:
        return "english"
    elif persian_arabic_chars > english_chars:
        return "persian_arabic"
    else:
        return "english"

def make_text_sticker(text, path):
    """ساخت استیکر متنی"""
    try:
        if not text or not text.strip():
            return False
        
        language = detect_language(text)
        
        if language == "persian_arabic":
            text = reshape_text(text)
        
        img_size = 512
        img = Image.new("RGBA", (img_size, img_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # استفاده از فونت پیش‌فرض
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        # محاسبه موقعیت متن
        try:
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            else:
                w, h = len(text) * 10, 20
        except:
            w, h = len(text) * 10, 20
        
        x = (img_size - w) / 2
        y = (img_size - h) / 2
        
        # رسم حاشیه سفید
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    if font:
                        draw.text((x + dx, y + dy), text, font=font, fill="white")
                    else:
                        draw.text((x + dx, y + dy), text, fill="white")
        
        # رسم متن اصلی
        if font:
            draw.text((x, y), text, fill="black", font=font)
        else:
            draw.text((x, y), text, fill="black")
        
        img.save(path, "PNG", optimize=True)
        return True
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        return False

def send_as_sticker(chat_id, text):
    """ارسال استیکر"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            sticker_path = tmp_file.name
        
        if not make_text_sticker(text, sticker_path):
            return False
        
        # تنظیم نام پک
        pack_name = f"pack_{chat_id}_by_{BOT_USERNAME}"
        pack_title = f"User {chat_id} Stickers"
        
        # بررسی وجود پک
        resp = requests.get(API + f"getStickerSet?name={pack_name}").json()
        
        with open(sticker_path, "rb") as f:
            files = {"png_sticker": f}
            
            if not resp.get("ok"):
                # ساخت پک جدید
                data = {
                    "user_id": chat_id,
                    "name": pack_name,
                    "title": pack_title,
                    "emojis": "🔥"
                }
                r = requests.post(API + "createNewStickerSet", data=data, files=files)
            else:
                # اضافه کردن به پک موجود
                data = {
                    "user_id": chat_id,
                    "name": pack_name,
                    "emojis": "🔥"
                }
                r = requests.post(API + "addStickerToSet", data=data, files=files)
        
        # حذف فایل موقت
        try:
            os.unlink(sticker_path)
        except:
            pass
        
        if r.json().get("ok"):
            # ارسال استیکر
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
        logger.error(f"Error sending sticker: {e}")
        return False

def process_message(message):
    """پردازش پیام‌های دریافتی"""
    try:
        chat_id = message["chat"]["id"]
        
        # ثبت کاربر جدید
        if chat_id not in user_data:
            user_data[chat_id] = {
                "id": chat_id,
                "first_name": message["from"].get("first_name", ""),
                "username": message["from"].get("username", ""),
                "joined": time.time(),
                "sticker_usage": [],
                "last_reset": time.time()
            }
        
        if "text" in message:
            text = message["text"]
            
            if text == "/start":
                send_welcome_message(chat_id)
                return
            elif text == "/help":
                send_help_message(chat_id)
                return
            else:
                # پردازش متن برای ساخت استیکر
                remaining, next_reset = check_sticker_limit(chat_id)
                if remaining <= 0:
                    next_reset_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_reset))
                    send_message(chat_id, f"⚠️ محدودیت روزانه شما تمام شده!\n\n🕒 زمان بعدی: {next_reset_time}")
                    return
                
                success = send_as_sticker(chat_id, text)
                if success:
                    record_sticker_usage(chat_id)
                    remaining, _ = check_sticker_limit(chat_id)
                    send_message(chat_id, f"✅ استیکر ساخته شد!\n📊 باقی‌مانده: {remaining}/5")
                else:
                    send_message(chat_id, "⚠️ خطا در ساخت استیکر")
                
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        send_message(chat_id, f"⚠️ خطایی رخ داد: {str(e)}")

def send_welcome_message(chat_id):
    """ارسال پیام خوش‌آمدگویی"""
    text = f"👋 سلام! به ربات استیکرساز خوش آمدید!\n\n"
    text += "با این ربات می‌توانید استیکرهای زیبا بسازید.\n\n"
    text += f"🔹 برای پشتیبانی: {SUPPORT_ID}\n"
    text += f"🔹 کانال ما: {CHANNEL_LINK}\n\n"
    text += "💡 فقط متن خود را ارسال کنید تا استیکر بسازم!"
    
    send_message(chat_id, text)

def send_help_message(chat_id):
    """ارسال پیام راهنما"""
    text = "🔹 راهنمای استفاده از ربات:\n\n"
    text += "1️⃣ برای ساخت استیکر، متن خود را ارسال کنید.\n"
    text += "2️⃣ هر روز 5 استیکر رایگان می‌توانید بسازید.\n"
    text += "3️⃣ برای استفاده نامحدود، اشتراک تهیه کنید.\n\n"
    text += "🔸 دستورات:\n"
    text += "/start - شروع مجدد ربات\n"
    text += "/help - راهنمای استفاده\n\n"
    text += f"🔹 برای پشتیبانی: {SUPPORT_ID}"
    
    send_message(chat_id, text)

def handler(event, context):
    """Vercel serverless function handler"""
    try:
        # Parse the request body
        if 'body' in event:
            if isinstance(event['body'], str):
                data = json.loads(event['body'])
            else:
                data = event['body']
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No body in request'})
            }
        
        logger.info(f"Received update: {data}")
        
        # Handle callback queries
        if "callback_query" in data:
            callback_query = data["callback_query"]
            query_id = callback_query["id"]
            # Acknowledge callback query
            requests.post(API + "answerCallbackQuery", json={"callback_query_id": query_id})
            return {
                'statusCode': 200,
                'body': 'OK'
            }
        
        # Process regular messages
        if "message" in data:
            process_message(data["message"])
            return {
                'statusCode': 200,
                'body': 'OK'
            }
        
        return {
            'statusCode': 200,
            'body': 'OK'
        }
        
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }