import os
import time
import re
import io
from datetime import datetime, timedelta
from flask import Flask, request
import threading

from dotenv import load_dotenv
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ========== Config ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # Railway provides this
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "@redoxbot_sticker")
FREE_LIMIT_PER_24H = int(os.getenv("FREE_LIMIT_PER_24H", "5"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "6053579919"))
PORT = int(os.getenv("PORT", "8000"))

bot = TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

# Runtime in-memory stores (for demo). For production, persist in Redis/DB.
USER_STATES = {}  # user_id -> dict(mode, step, data)
QUOTAS = {}       # user_id -> dict(used, reset_at)

# ========== Helpers ==========
def slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^\w\-]+", "", s)
    s = re.sub(r"_+", "_", s)
    return s or f"pack_{int(time.time())}"

def is_member(user_id: int) -> bool:
    try:
        m = bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return True

def ensure_member(message) -> bool:
    uid = message.from_user.id
    if is_member(uid):
        return True
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('@','')}"))
    kb.add(InlineKeyboardButton("I Joined ✅", callback_data="recheck_sub"))
    bot.reply_to(message, f"Please join {FORCE_SUB_CHANNEL} to continue.", reply_markup=kb)
    return False

def get_quota(uid: int) -> dict:
    now = time.time()
    q = QUOTAS.get(uid)
    if not q or now >= q["reset_at"]:
        QUOTAS[uid] = {"used": 0, "reset_at": now + 24*3600}
    return QUOTAS[uid]

def quota_left(uid: int) -> int:
    q = get_quota(uid)
    return max(0, FREE_LIMIT_PER_24H - q["used"])

def use_quota(uid: int) -> bool:
    q = get_quota(uid)
    if q["used"] >= FREE_LIMIT_PER_24H:
        return False
    q["used"] += 1
    return True

def ms_timer(seconds_left: int) -> str:
    h = seconds_left // 3600
    m = (seconds_left % 3600) // 60
    s = seconds_left % 60
    return f"{h}h {m}m {s}s"

def shape_rtl(text: str) -> str:
    reshaped = arabic_reshaper.reshape(text)
    bidi = get_display(reshaped)
    return bidi

def best_font(size: int) -> ImageFont.FreeTypeFont:
    try_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for p in try_paths:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            continue
    return ImageFont.load_default()

def wrap_and_fit(draw: ImageDraw.ImageDraw, text: str, max_w: int, max_h: int, base_size: int = 40, min_size: int = 14):
    size = base_size
    lines = []
    while size >= min_size:
        font = best_font(size)
        words = (text or "").split()
        if not words:
            lines = [""]
            return lines, font, size
        lines = []
        line = ""
        for w in words:
            test = (line + " " + w).strip() if line else w
            w_px, _ = draw.textsize(test, font=font)
            if w_px > max_w and line:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        total_h = int(len(lines) * size * 1.25)
        if total_h <= max_h:
            return lines, font, size
        size -= 2
    font = best_font(min_size)
    return lines, font, min_size

def render_png_512(text: str, anchor: str, color: str, font_size: int, auto_fit: bool,
                   bg_type: str = "transparent", bg_color: str = "#000000", bg_image_bytes: bytes | None = None) -> bytes:
    W = H = 512
    padding = 24
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_type == "color":
        bg = Image.new("RGBA", (W, H), ImageColor_get(bg_color, (0,0,0,255)))
        img.alpha_composite(bg)
    elif bg_type == "image" and bg_image_bytes:
        try:
            bimg = Image.open(io.BytesIO(bg_image_bytes)).convert("RGBA")
            scale = max(W / bimg.width, H / bimg.height)
            dw, dh = int(bimg.width * scale), int(bimg.height * scale)
            bimg = bimg.resize((dw, dh), Image.LANCZOS)
            ox, oy = (W - dw)//2, (H - dh)//2
            img.alpha_composite(bimg, (ox, oy))
        except Exception:
            pass

    safe_text = shape_rtl(text or "")
    drawable_w = W - padding*2
    drawable_h = H - padding*2
    if auto_fit:
        lines, font, size = wrap_and_fit(draw, safe_text, drawable_w, drawable_h, base_size=font_size)
    else:
        font = best_font(font_size)
        words = (safe_text or "").split()
        lines = []
        line = ""
        for w in words:
            test = (line + " " + w).strip() if line else w
            w_px, _ = draw.textsize(test, font=font)
            if w_px > drawable_w and line:
                lines.append(line)
                line = w
            else:
                line = test
        if line:
            lines.append(line)
        size = font_size

    total_h = int(len(lines) * size * 1.25)
    if anchor == "center-right":
        y = (H - total_h)//2
    elif anchor == "bottom-right":
        y = H - padding - total_h
    else:
        y = padding

    x = W - padding
    for i, ln in enumerate(lines):
        yy = y + int(i * size * 1.25)
        draw.text((x+2, yy+2), ln, font=font, fill=(0,0,0,90), anchor="ra")
        draw.text((x, yy), ln, font=font, fill=ImageColor_get(color, (255,255,255,255)), anchor="ra")

    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()

def ImageColor_get(c: str, fallback=(255,255,255,255)):
    from PIL import ImageColor
    try:
        rgba = ImageColor.getcolor(c, "RGBA")
        return rgba
    except Exception:
        return fallback

def download_telegram_file(file_id: str) -> bytes | None:
    try:
        file_info = bot.get_file(file_id)
        return bot.download_file(file_info.file_path)
    except Exception:
        return None

def set_state(uid: int, mode: str, step: str, data: dict | None = None):
    USER_STATES[uid] = {"mode": mode, "step": step, "data": data or {}}

def get_state(uid: int):
    return USER_STATES.get(uid)

def clear_state(uid: int):
    USER_STATES.pop(uid, None)

def main_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("Simple Sticker 🪄", callback_data="simple"),
        InlineKeyboardButton("Advanced 🤖", callback_data="advanced"),
    )
    kb.row(
        InlineKeyboardButton("Rename Pack ✏️", callback_data="rename"),
        InlineKeyboardButton("Help ℹ️", callback_data="help"),
    )
    kb.row(
        InlineKeyboardButton("Support 🛟", url="https://t.me/onedaytoalive")
    )
    return kb

# ========== Bot Handlers ==========
@bot.message_handler(commands=["start"])
def on_start(message):
    if not ensure_member(message): return
    bot.reply_to(message, "Welcome! Choose an option:", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "recheck_sub")
def on_recheck_sub(call):
    if is_member(call.from_user.id):
        bot.answer_callback_query(call.id, "Thanks! You're in.")
        bot.edit_message_text("You're verified. Choose:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "Still not a member. Join and try again.")

@bot.callback_query_handler(func=lambda c: c.data == "help")
def on_help(call):
    text = ("• Simple: pack name → photo → text → PNG + pack link\n"
            "• Advanced: pack name → background (transparent/color/image) → text → position → color → font size → confirm → PNG\n"
            f"• Forced join: must be in {FORCE_SUB_CHANNEL}\n"
            f"• Free limit: {FREE_LIMIT_PER_24H} advanced stickers per 24h")
    bot.answer_callback_query(call.id)
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "simple")
def on_simple(call):
    uid = call.from_user.id
    if not is_member(uid):
        bot.answer_callback_query(call.id, "Join the channel first.")
        bot.send_message(call.message.chat.id, f"Please join {FORCE_SUB_CHANNEL} to continue.")
        return
    set_state(uid, "simple", "ask_pack", {})
    bot.answer_callback_query(call.id)
    bot.edit_message_text("Simple Maker — send pack name:", chat_id=call.message.chat.id, message_id=call.message.message_id)

@bot.message_handler(content_types=["text", "photo"])
def on_message_router(message):
    uid = message.from_user.id
    st = get_state(uid)
    if not st:
        return
    mode, step, data = st["mode"], st["step"], st["data"]

    # SIMPLE FLOW
    if mode == "simple":
        if step == "ask_pack" and message.content_type == "text":
            data["pack_name"] = message.text.strip()
            set_state(uid, mode, "ask_photo", data)
            bot.reply_to(message, "Great! Now send a photo (PNG/JPG).")
            return

        if step == "ask_photo" and message.content_type == "photo":
            file_id = message.photo[-1].file_id
            data["photo_bytes"] = download_telegram_file(file_id)
            if not data["photo_bytes"]:
                bot.reply_to(message, "Failed to download photo, try again.")
                return
            set_state(uid, mode, "ask_text", data)
            bot.reply_to(message, "Optional: send text for the sticker (or send /skip).")
            return

        if step == "ask_text" and message.content_type == "text":
            if message.text.strip() == "/skip":
                data["text"] = ""
            else:
                data["text"] = message.text.strip()

            try:
                bg = Image.open(io.BytesIO(data["photo_bytes"])).convert("RGBA")
                W = H = 512
                scale = max(W / bg.width, H / bg.height)
                bg = bg.resize((int(bg.width*scale), int(bg.height*scale)), Image.LANCZOS)
                canvas = Image.new("RGBA", (W, H), (0,0,0,0))
                ox, oy = (W-bg.width)//2, (H-bg.height)//2
                canvas.alpha_composite(bg, (ox, oy))

                shaped = shape_rtl(data["text"])
                draw = ImageDraw.Draw(canvas)
                padding = 24
                lines, font, size = wrap_and_fit(draw, shaped, W - 2*padding, H - 2*padding, base_size=40)
                total_h = int(len(lines) * size * 1.25)
                y = padding
                x = W - padding
                for i, ln in enumerate(lines):
                    yy = y + int(i * size * 1.25)
                    draw.text((x+2, yy+2), ln, font=font, fill=(0,0,0,90), anchor="ra")
                    draw.text((x, yy), ln, font=font, fill=(255,255,255,255), anchor="ra")

                bio = io.BytesIO()
                canvas.save(bio, format="PNG")
                bio.seek(0)

                pack_slug = slugify(data["pack_name"])
                bot.send_document(message.chat.id, bio, visible_file_name="sticker.png",
                                  caption=f"Pack link: https://t.me/addstickers/{pack_slug}")
            except Exception as e:
                bot.reply_to(message, f"Error while creating sticker: {e}")
            finally:
                clear_state(uid)
            return

    # ADVANCED FLOW (similar structure, abbreviated for space)
    if mode == "advanced":
        if step == "ask_pack" and message.content_type == "text":
            data["pack_name"] = message.text.strip()
            set_state(uid, mode, "choose_bg", data)
            kb = InlineKeyboardMarkup()
            kb.row(InlineKeyboardButton("Transparent", callback_data="a_bg_trans"),
                   InlineKeyboardButton("Color", callback_data="a_bg_color"),
                   InlineKeyboardButton("Image", callback_data="a_bg_image"))
            bot.reply_to(message, "Choose background:", reply_markup=kb)
            return
        # ... (rest of advanced flow handlers)

@bot.callback_query_handler(func=lambda c: c.data == "advanced")
def on_advanced(call):
    uid = call.from_user.id
    if not is_member(uid):
        bot.answer_callback_query(call.id, "Join the channel first.")
        bot.send_message(call.message.chat.id, f"Please join {FORCE_SUB_CHANNEL} to continue.")
        return
    left = quota_left(uid)
    if left <= 0:
        q = get_quota(uid)
        seconds_left = max(1, int(q["reset_at"] - time.time()))
        bot.answer_callback_query(call.id, "Limit reached.")
        bot.edit_message_text(f"Your free daily limit is over. Try again in {ms_timer(seconds_left)}.",
                              chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu())
        return
    set_state(uid, "advanced", "ask_pack", {})
    bot.answer_callback_query(call.id)
    bot.edit_message_text(f"Advanced Maker — send pack name (left today: {left})",
                          chat_id=call.message.chat.id, message_id=call.message.message_id)

# ========== Flask Webhook ==========
@app.route('/')
def index():
    return "Telegram Bot is running! 🤖"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK"
    else:
        return "Bad Request", 400

def setup_webhook():
    """Setup webhook for Railway deployment"""
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=webhook_url)
            print(f"Webhook set to: {webhook_url}")
        except Exception as e:
            print(f"Failed to set webhook: {e}")
    else:
        print("No WEBHOOK_URL provided, webhook not set")

if __name__ == "__main__":
    print("Starting Telegram Bot for Railway...")
    
    if WEBHOOK_URL:
        # Production mode with webhook
        setup_webhook()
        app.run(host="0.0.0.0", port=PORT)
    else:
        # Development mode with polling
        print("Running in polling mode (development)")
        try:
            bot.remove_webhook()
            time.sleep(2)
            bot.infinity_polling(skip_pending=True, allowed_updates=["message","callback_query"])
        except Exception as e:
            print(f"Polling failed: {e}")
