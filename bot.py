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

# ========== Compatibility Helper ==========
def get_text_size(draw, text, font):
    """Compatible text size function for both old and new Pillow versions"""
    try:
        # Try new method first (Pillow 8.0.0+)
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except AttributeError:
        # Fallback to old method (Pillow < 8.0.0)
        return draw.textsize(text, font=font)

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
    try:
        # Ensure text is properly encoded as UTF-8
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        elif not isinstance(text, str):
            text = str(text)
        
        # Handle empty or None text
        if not text or text.strip() == "":
            return ""
            
        # Process Persian/Arabic text
        reshaped = arabic_reshaper.reshape(text)
        bidi = get_display(reshaped)
        return bidi
    except Exception as e:
        # Fallback to original text if reshaping fails
        print(f"Text shaping error: {e}")
        return str(text) if text else ""

def best_font(size: int) -> ImageFont.FreeTypeFont:
    try_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
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
            w_px, _ = get_text_size(draw, test, font)
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

def safe_text_encode(text):
    """Safely encode text to handle Persian/Arabic characters"""
    if not text:
        return ""
    
    # Convert to string if needed
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8')
        except UnicodeDecodeError:
            text = text.decode('utf-8', errors='ignore')
    elif not isinstance(text, str):
        text = str(text)
    
    # Remove any problematic characters that cause latin-1 errors
    try:
        # Test if text can be safely processed
        text.encode('utf-8').decode('utf-8')
        return text
    except (UnicodeError, UnicodeEncodeError, UnicodeDecodeError):
        # Clean the text by removing problematic characters
        import unicodedata
        # Normalize and remove control characters
        text = unicodedata.normalize('NFKD', text)
        # Keep only printable characters
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
        return text

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

    # Safely process input text with comprehensive encoding protection
    input_text = safe_text_encode(text or "")
    
    # Process text with RTL shaping and encoding safety
    try:
        safe_text = shape_rtl(input_text)
        safe_text = safe_text_encode(safe_text)  # Double-check encoding
    except Exception as e:
        print(f"Text processing error: {e}")
        safe_text = input_text  # Fallback to cleaned input
    
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
            w_px, _ = get_text_size(draw, test, font)
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
        
        # Ensure each line is safely encoded before drawing
        ln = safe_text_encode(ln)
        if not ln or ln.strip() == "":  # Skip empty lines
            continue
            
        # Draw text with comprehensive error handling
        try:
            # Try modern Pillow anchor method first
            draw.text((x+2, yy+2), ln, font=font, fill=(0,0,0,90), anchor="ra")
            draw.text((x, yy), ln, font=font, fill=ImageColor_get(color, (255,255,255,255)), anchor="ra")
        except (TypeError, AttributeError, UnicodeEncodeError, UnicodeError):
            # Fallback for older Pillow versions or encoding issues
            try:
                text_w, text_h = get_text_size(draw, ln, font)
                draw.text((x-text_w+2, yy+2), ln, font=font, fill=(0,0,0,90))
                draw.text((x-text_w, yy), ln, font=font, fill=ImageColor_get(color, (255,255,255,255)))
            except (UnicodeEncodeError, UnicodeError) as e:
                # Final fallback: try to draw ASCII-safe version
                try:
                    ascii_safe = ln.encode('ascii', errors='ignore').decode('ascii')
                    if ascii_safe:
                        text_w, text_h = get_text_size(draw, ascii_safe, font)
                        draw.text((x-text_w+2, yy+2), ascii_safe, font=font, fill=(0,0,0,90))
                        draw.text((x-text_w, yy), ascii_safe, font=font, fill=ImageColor_get(color, (255,255,255,255)))
                    else:
                        print(f"Skipping line due to encoding issues: {repr(ln)}")
                except Exception as final_e:
                    print(f"Final text drawing error for line: {final_e}")
                    continue  # Skip this line completely
            except Exception as e:
                print(f"Text drawing error for line '{repr(ln)}': {e}")
                continue  # Skip this line if it can't be drawn

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
                # Ensure text is properly encoded
                user_text = message.text.strip()
                data["text"] = safe_text_encode(user_text)

            try:
                bg = Image.open(io.BytesIO(data["photo_bytes"])).convert("RGBA")
                W = H = 512
                scale = max(W / bg.width, H / bg.height)
                bg = bg.resize((int(bg.width*scale), int(bg.height*scale)), Image.LANCZOS)
                canvas = Image.new("RGBA", (W, H), (0,0,0,0))
                ox, oy = (W-bg.width)//2, (H-bg.height)//2
                canvas.alpha_composite(bg, (ox, oy))

                # Safely process text with comprehensive encoding protection
                text_content = safe_text_encode(data.get("text", ""))
                
                try:
                    shaped = shape_rtl(text_content)
                    shaped = safe_text_encode(shaped)  # Double-check encoding
                except Exception as e:
                    print(f"Text shaping error: {e}")
                    shaped = text_content  # Fallback to cleaned input
                
                draw = ImageDraw.Draw(canvas)
                padding = 24
                lines, font, size = wrap_and_fit(draw, shaped, W - 2*padding, H - 2*padding, base_size=40)
                total_h = int(len(lines) * size * 1.25)
                y = padding
                x = W - padding
                for i, ln in enumerate(lines):
                    yy = y + int(i * size * 1.25)
                    
                    # Ensure line is safely encoded
                    ln = safe_text_encode(ln)
                    if not ln or ln.strip() == "":  # Skip empty lines
                        continue
                        
                    try:
                        draw.text((x+2, yy+2), ln, font=font, fill=(0,0,0,90), anchor="ra")
                        draw.text((x, yy), ln, font=font, fill=(255,255,255,255), anchor="ra")
                    except (TypeError, AttributeError, UnicodeEncodeError, UnicodeError):
                        try:
                            text_w, text_h = get_text_size(draw, ln, font)
                            draw.text((x-text_w+2, yy+2), ln, font=font, fill=(0,0,0,90))
                            draw.text((x-text_w, yy), ln, font=font, fill=(255,255,255,255))
                        except (UnicodeEncodeError, UnicodeError):
                            # Final fallback: ASCII-safe version
                            try:
                                ascii_safe = ln.encode('ascii', errors='ignore').decode('ascii')
                                if ascii_safe:
                                    text_w, text_h = get_text_size(draw, ascii_safe, font)
                                    draw.text((x-text_w+2, yy+2), ascii_safe, font=font, fill=(0,0,0,90))
                                    draw.text((x-text_w, yy), ascii_safe, font=font, fill=(255,255,255,255))
                                else:
                                    print(f"Skipping line due to encoding issues: {repr(ln)}")
                            except Exception as final_e:
                                print(f"Final text drawing error: {final_e}")
                                continue
                        except Exception as e:
                            print(f"Text drawing error: {e}")
                            continue

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

    # ADVANCED FLOW
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

        if step == "ask_text" and message.content_type == "text":
            # Ensure text is properly encoded for advanced flow
            user_text = message.text.strip()
            data["text"] = safe_text_encode(user_text)
            set_state(uid, mode, "ask_anchor", data)
            kb = InlineKeyboardMarkup()
            kb.row(InlineKeyboardButton("Top-Right", callback_data="a_pos_tr"),
                   InlineKeyboardButton("Center-Right", callback_data="a_pos_cr"),
                   InlineKeyboardButton("Bottom-Right", callback_data="a_pos_br"))
            bot.reply_to(message, "Choose text position:", reply_markup=kb)
            return

        if step == "ask_color" and message.content_type == "text":
            color = message.text.strip()
            if not re.match(r"^#([0-9a-fA-F]{6})$", color):
                bot.reply_to(message, "Send a HEX color like #ffffff")
                return
            data["color"] = color
            set_state(uid, mode, "ask_font", data)
            bot.reply_to(message, "Send font size (18–72). Example: 40")
            return

        if step == "ask_font" and message.content_type == "text":
            try:
                sz = int(message.text.strip())
                if not (18 <= sz <= 72):
                    raise ValueError()
                data["font_size"] = sz
            except Exception:
                bot.reply_to(message, "Number between 18 and 72, please.")
                return
            set_state(uid, mode, "confirm", data)
            kb = InlineKeyboardMarkup()
            kb.row(InlineKeyboardButton("Yes, create ✅", callback_data="a_confirm_yes"),
                   InlineKeyboardButton("No, edit", callback_data="a_confirm_no"))
            bot.reply_to(message, "Are you happy with the result?", reply_markup=kb)
            return

        if step == "bg_image" and message.content_type == "photo":
            data["bg_image_bytes"] = download_telegram_file(message.photo[-1].file_id)
            set_state(uid, mode, "ask_text", data)
            bot.reply_to(message, "Send text for sticker")
            return

        if step == "bg_color" and message.content_type == "text":
            color = message.text.strip()
            if not re.match(r"^#([0-9a-fA-F]{6})$", color):
                bot.reply_to(message, "Send a HEX color like #000000")
                return
            data["bg_color"] = color
            set_state(uid, mode, "ask_text", data)
            bot.reply_to(message, "Send text for sticker")
            return

    # RENAME FLOW (placeholder)
    if mode == "rename":
        if step == "ask_old" and message.content_type == "text":
            data["old_name"] = message.text.strip()
            set_state(uid, mode, "ask_new", data)
            bot.reply_to(message, "Send new pack name")
            return
        if step == "ask_new" and message.content_type == "text":
            data["new_name"] = message.text.strip()
            bot.reply_to(message, f"Pack renamed from {data['old_name']} to {data['new_name']} (demo).")
            clear_state(uid)
            return

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

@bot.callback_query_handler(func=lambda c: c.data == "rename")
def on_rename(call):
    uid = call.from_user.id
    if not is_member(uid):
        bot.answer_callback_query(call.id, "Join the channel first.")
        bot.send_message(call.message.chat.id, f"Please join {FORCE_SUB_CHANNEL} to continue.")
        return
    set_state(uid, "rename", "ask_old", {})
    bot.answer_callback_query(call.id)
    bot.edit_message_text("Send current pack name:", chat_id=call.message.chat.id, message_id=call.message.message_id)

# Advanced background choices
@bot.callback_query_handler(func=lambda c: c.data in ("a_bg_trans","a_bg_color","a_bg_image","a_pos_tr","a_pos_cr","a_pos_br","a_confirm_yes","a_confirm_no"))
def on_advanced_steps(call):
    uid = call.from_user.id
    st = get_state(uid)
    if not st or st["mode"] != "advanced":
        bot.answer_callback_query(call.id)
        return
    data = st["data"]

    if call.data == "a_bg_trans":
        data["bg_type"] = "transparent"
        set_state(uid, "advanced", "ask_text", data)
        bot.answer_callback_query(call.id, "Transparent selected")
        bot.edit_message_text("Send text for sticker", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if call.data == "a_bg_color":
        data["bg_type"] = "color"
        set_state(uid, "advanced", "bg_color", data)
        bot.answer_callback_query(call.id, "Color selected")
        bot.edit_message_text("Send HEX color like #000000", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if call.data == "a_bg_image":
        data["bg_type"] = "image"
        set_state(uid, "advanced", "bg_image", data)
        bot.answer_callback_query(call.id, "Image selected")
        bot.edit_message_text("Send background image", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if call.data in ("a_pos_tr","a_pos_cr","a_pos_br"):
        anchor = {"a_pos_tr":"top-right", "a_pos_cr":"center-right", "a_pos_br":"bottom-right"}[call.data]
        data["anchor"] = anchor
        set_state(uid, "advanced", "ask_color", data)
        bot.answer_callback_query(call.id, f"Position: {anchor}")
        bot.edit_message_text("Send text color (HEX like #ffffff)", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if call.data == "a_confirm_no":
        bot.answer_callback_query(call.id, "Edit your choices.")
        bot.edit_message_text("Okay, adjust options and try again.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if call.data == "a_confirm_yes":
        if not use_quota(uid):
            q = get_quota(uid)
            seconds_left = max(1, int(q["reset_at"] - time.time()))
            bot.answer_callback_query(call.id, "Limit reached.")
            bot.edit_message_text(f"Your free daily limit is over. Try again in {ms_timer(seconds_left)}.",
                                  chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=main_menu())
            clear_state(uid)
            return

        pack_name = data.get("pack_name") or f"pack_{uid}"
        text = data.get("text","")
        anchor = data.get("anchor","top-right")
        color = data.get("color","#ffffff")
        font_size = int(data.get("font_size", 40))
        bg_type = data.get("bg_type","transparent")
        bg_color = data.get("bg_color","#000000")
        bg_bytes = data.get("bg_image_bytes")

        try:
            png = render_png_512(text=text, anchor=anchor, color=color, font_size=font_size, auto_fit=True,
                                 bg_type=bg_type, bg_color=bg_color, bg_image_bytes=bg_bytes)
            bio = io.BytesIO(png)
            pack_slug = slugify(pack_name)
            bot.answer_callback_query(call.id, "Created!")
            bot.send_document(call.message.chat.id, bio, visible_file_name="sticker.png",
                              caption=f"Pack link: https://t.me/addstickers/{pack_slug}")
        except Exception as e:
            bot.answer_callback_query(call.id, "Failed.")
            bot.send_message(call.message.chat.id, f"Error: {e}")
        finally:
            clear_state(uid)
        return

# Safety: unknown callbacks
@bot.callback_query_handler(func=lambda c: True)
def unknown_cb(call):
    bot.answer_callback_query(call.id, "Select from the menu.")

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
            # Ensure webhook is completely removed first
            print("Removing any existing webhook...")
            bot.remove_webhook()
            time.sleep(3)
            
            # Set new webhook
            print(f"Setting webhook to: {webhook_url}")
            result = bot.set_webhook(url=webhook_url)
            if result:
                print("✅ Webhook set successfully!")
            else:
                print("❌ Failed to set webhook")
                
            # Verify webhook is set
            webhook_info = bot.get_webhook_info()
            print(f"Current webhook URL: {webhook_info.url}")
            print(f"Pending updates: {webhook_info.pending_update_count}")
            
        except Exception as e:
            print(f"Failed to set webhook: {e}")
    else:
        print("No WEBHOOK_URL provided, webhook not set")

if __name__ == "__main__":
    print("Starting Telegram Bot for Railway...")
    
    # Force webhook removal with multiple attempts
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1}/{max_attempts}: Clearing webhooks...")
            bot.remove_webhook()
            time.sleep(2)
            
            # Verify webhook is actually removed
            webhook_info = bot.get_webhook_info()
            if not webhook_info.url:
                print("✅ Webhook successfully removed")
                break
            else:
                print(f"⚠️ Webhook still active: {webhook_info.url}")
                if attempt < max_attempts - 1:
                    print("Retrying...")
                    time.sleep(3)
        except Exception as e:
            print(f"Warning: Could not clear webhook (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(2)
    
    # Additional wait to ensure cleanup
    print("Waiting for complete cleanup...")
    time.sleep(5)
    
    if WEBHOOK_URL:
        # Production mode with webhook
        print("Setting up webhook for production...")
        setup_webhook()
        print(f"Starting Flask server on port {PORT}")
        app.run(host="0.0.0.0", port=PORT)
    else:
        # Development mode with polling - should not happen on Railway
        print("⚠️ WARNING: No WEBHOOK_URL found!")
        print("Railway deployments should use webhooks, not polling.")
        print("Please set WEBHOOK_URL environment variable to your Railway app URL.")
        print("Example: https://your-app-name.up.railway.app")
        
        # Try polling anyway with extra safety
        try:
            # Final webhook check
            webhook_info = bot.get_webhook_info()
            if webhook_info.url:
                print(f"❌ Webhook still active: {webhook_info.url}")
                print("Forcing webhook removal...")
                bot.remove_webhook()
                time.sleep(5)
            
            print("Starting polling (not recommended for Railway)...")
            bot.infinity_polling(skip_pending=True, allowed_updates=["message","callback_query"])
        except Exception as e:
            print(f"❌ Polling failed: {e}")
            if "409" in str(e) or "Conflict" in str(e):
                print("\n🔧 SOLUTION:")
                print("1. Set WEBHOOK_URL environment variable in Railway")
                print("2. Restart your Railway deployment")
                print("3. Make sure no other instances are running")
                print("4. Check Railway logs for multiple processes")
            else:
                print(f"Unexpected error: {e}")
