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
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "@YourChannel")
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
    # … باقی webhook logic …

def reshape_text(text):
    """اصلاح متن فارسی/عربی با arabic_reshaper و bidi"""
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as e:
        logger.error(f"Error reshaping text: {e}")
        return text

def sanitize_pack_name(text):
    """تبدیل نام پک به فرمت قابل قبول برای Telegram"""
    import unicodedata
    sanitized = ""
    for char in text:
        if char.isalnum() and ord(char) < 128:
            sanitized += char
        elif char.isspace():
            sanitized += "_"
        elif '\u0600' <= char <= '\u06FF':
            persian_to_english = {
                'ا':'a','ب':'b','پ':'p','ت':'t','ث':'s','ج':'j','چ':'ch',
                'ح':'h','خ':'kh','د':'d','ذ':'z','ر':'r','ز':'z','ژ':'zh',
                'س':'s','ش':'sh','ص':'s','ض':'z','ط':'t','ظ':'z','ع':'a',
                'غ':'gh','ف':'f','ق':'gh','ک':'k','گ':'g','ل':'l','م':'m',
                'ن':'n','و':'v','ه':'h','ی':'y','ئ':'e','ء':'a'
            }
            sanitized += persian_to_english.get(char, 'x')
        else:
            continue
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    if not sanitized or len(sanitized) < 2:
        sanitized = "pack"
    return sanitized[:64]

def _measure_text(draw, text, font):
    """اندازه‌گیری امن متن"""
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        return bbox[2]-bbox[0], bbox[3]-bbox[1]
    except:
        try:
            return draw.textsize(text, font=font)
        except:
            return len(text)*max(font.size//2,1), font.size

def _hard_wrap_word(draw, word, font, max_width):
    """شکستن کلمات خیلی بلند به بخش‌های کوچکتر"""
    parts, start = [], 0
    n = len(word)
    if n == 0:
        return [word]
    while start < n:
        lo, hi, best = 1, n-start, 1
        while lo <= hi:
            mid = (lo+hi)//2
            seg = word[start:start+mid]
            w,_ = _measure_text(draw, seg, font)
            if w <= max_width:
                best = mid; lo = mid+1
            else:
                hi = mid-1
        parts.append(word[start:start+best])
        start += best
        if best == 0:
            break
    return parts

def wrap_text_multiline(draw, text, font, max_width, is_rtl=False):
    """شکستن متن به خطوط متعدد با RTL/LTR"""
    if not text:
        return [""]
    tokens = re.split(r"(\s+)", text)
    lines, current = [], ""
    for tk in tokens:
        if tk.strip() == "":
            tentative = (tk+current) if is_rtl else (current+tk)
            w,_ = _measure_text(draw, tentative, font)
            if w <= max_width:
                current = tentative
            else:
                if current:
                    lines.append(current.rstrip())
                    current = ""
            continue
        tentative = (tk+current) if is_rtl else (current+tk)
        w,_ = _measure_text(draw, tentative, font)
        if w <= max_width:
            current = tentative
        else:
            if current:
                lines.append(current.rstrip())
            for part in _hard_wrap_word(draw, tk, font, max_width):
                pw,_ = _measure_text(draw, part, font)
                if current == "" and pw <= max_width:
                    current = part
                else:
                    if current:
                        lines.append(current.rstrip())
                    current = part
    if current:
        lines.append(current.rstrip())
    # برای RTL پاکسازی اضافات
    if is_rtl:
        return [ln.strip() for ln in lines if ln.strip()]
    return lines or [""]

def measure_multiline_block(draw, lines, font, line_spacing_px):
    """محاسبه اندازه بلوک چندخطی"""
    max_w, total_h = 0, 0
    for i, ln in enumerate(lines):
        w, h = _measure_text(draw, ln, font)
        max_w = max(max_w, w)
        total_h += h + (line_spacing_px if i < len(lines)-1 else 0)
    return max_w, total_h

def detect_language(text):
    """تشخیص زبان متن"""
    pa = len(re.findall(r'[\u0600-\u06FF]', text))
    en = len(re.findall(r'[a-zA-Z]', text))
    if pa > en:
        return "persian_arabic"
    if en > 0:
        return "english"
    return "other"

def get_font(size, language="english"):
    """بارگذاری فونت بر اساس زبان"""
    if language == "persian_arabic":
        font_paths = [
            "Vazirmatn-Regular.ttf", "IRANSans.ttf", "Vazir.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
    else:
        font_paths = [
            "arial.ttf", "DejaVuSans.ttf",
            "/Windows/Fonts/arial.ttf"
        ]
    for p in font_paths:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()
    def make_text_sticker(text, path, background_file_id=None):
    try:
        logger.info(f"Creating sticker with text: {text}")
        language = detect_language(text)
        is_rtl = (language == "persian_arabic")
        if is_rtl:
            text = reshape_text(text)

        img_size = 256
        img = Image.new("RGBA", (img_size, img_size), (255,255,255,0))

        if background_file_id:
            try:
                info = requests.get(API + f"getFile?file_id={background_file_id}").json()
                if info.get("ok"):
                    fp = info["result"]["file_path"]
                    res = requests.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fp}")
                    if res.status_code == 200:
                        bg = Image.open(BytesIO(res.content)).convert("RGBA")
                        bg = bg.resize((img_size, img_size))
                        img.paste(bg, (0,0))
            except Exception as e:
                logger.error(f"Error loading background: {e}")

        draw = ImageDraw.Draw(img)
        initial = 200 if is_rtl else 180
        minimum =  40 if is_rtl else  50
        max_w = max_h = img_size - 20

        font_size = initial
        font = get_font(font_size, language) or ImageFont.load_default()

        while font_size >= minimum:
            spacing = max(int(font_size * 0.15),4)
            lines = wrap_text_multiline(draw, text, font, max_w, is_rtl)
            bw, bh = measure_multiline_block(draw, lines, font, spacing)
            if bw <= max_w and bh <= max_h:
                break
            font_size -= 3
            font = get_font(font_size, language) or ImageFont.load_default()

        y = 10
        for line in lines:
            lw, lh = _measure_text(draw, line, font)
            x = img_size - lw - 10 if is_rtl else (img_size - lw)//2
            # white outline
            for off in (1,):
                for dx,dy in [(-off,-off),(off,off),(off,-off),(-off,off)]:
                    draw.text((x+dx, y+dy), line, font=font, fill="white")
            # main text
            draw.text((x, y), line, font=font, fill="black")
            y += lh + spacing

        final = img.resize((512,512), Image.LANCZOS)
        final.save(path, "PNG", optimize=True, compress_level=9)
        if os.path.getsize(path) > 512*1024:
            final.save(path, "PNG", optimize=True, compress_level=9, quality=85)
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
    if chat_id not in user_data:
        return 5, time.time() + 24*3600

    current_time = time.time()
    user_info = user_data[chat_id]
    last_reset = user_info.get("last_reset", current_time)
    next_reset = last_reset + 24*3600

    if current_time >= next_reset:
        user_info["sticker_usage"] = []
        user_info["last_reset"] = current_time
        next_reset = current_time + 24*3600
        save_user_data()

    used = len(user_info.get("sticker_usage", []))
    remaining = max(0, 5 - used)
    return remaining, next_reset

def record_sticker_usage(chat_id):
    if chat_id not in user_data:
        user_data[chat_id] = {
            "mode": None, "count":0, "step":None,
            "pack_name":None, "background":None,
            "created_packs":[], "sticker_usage":[],
            "last_reset": time.time()
        }
    current_time = time.time()
    info = user_data[chat_id]
    last_reset = info.get("last_reset", current_time)
    if current_time >= last_reset + 24*3600:
        info["sticker_usage"] = []
        info["last_reset"] = current_time
    info["sticker_usage"].append(current_time)
    save_user_data()

def get_user_packs_from_api(chat_id):
    try:
        resp = requests.get(API + f"getChat?chat_id={chat_id}").json()
        first = resp.get("result",{}).get("first_name","User")
        packs = []
        current = user_data.get(chat_id,{}).get("pack_name")
        if current:
            r2 = requests.get(API + f"getStickerSet?name={current}").json()
            if r2.get("ok"):
                packs.append({"name":current,"title":f"{first}'s Stickers"})
        return packs
    except Exception as e:
        logger.error(f"Error getting packs: {e}")
        return []

def check_channel_membership(chat_id):
    try:
        if CHANNEL_LINK.startswith("@"):
            ch = CHANNEL_LINK[1:]
        elif "t.me/" in CHANNEL_LINK:
            ch = CHANNEL_LINK.split("t.me/")[-1].lstrip("@")
        else:
            ch = CHANNEL_LINK
        resp = requests.get(API + "getChatMember", params={
            "chat_id": f"@{ch}",
            "user_id": chat_id
        }).json()
        if resp.get("ok"):
            status = resp["result"]["status"]
            return status in ["member","administrator","creator"]
        return False
    except Exception as e:
        logger.error(f"Error in membership check: {e}")
        return False
        def send_membership_required_message(chat_id):
    message = f"""🔒 عضویت در کانال اجباری است!

برای استفاده از ربات، ابتدا باید عضو کانال ما شوید:

📢 {CHANNEL_LINK}

بعد از عضویت، دوباره /start را بزنید."""
    keyboard = {
        "inline_keyboard": [[
            {"text":"📢 عضویت در کانال","url":f"https://t.me/{CHANNEL_LINK.lstrip('@')}"}
        ]]
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": message,
        "reply_markup": keyboard
    })

def send_message(chat_id, text):
    requests.post(API + "sendMessage", json={"chat_id":chat_id, "text":text})

if __name__ == "__main__":
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        resp = requests.get(API + f"setWebhook?url={webhook_url}")
        logger.info(f"setWebhook: {resp.json()}")
    else:
        logger.warning("⚠️ APP_URL is not set. Webhook not registered.")
    port = int(os.environ.get("PORT", 8080))
    serve(app, host="0.0.0.0", port=port)
        
