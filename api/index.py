#!/usr/bin/env python3
"""
Complete integrated Telegram Bot for Vercel
All code in one file to avoid import issues
"""

import os
import json
import logging
import asyncio
import random
import tempfile
import io
import base64
from datetime import datetime
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputSticker
from telegram.error import BadRequest
import re
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ADMIN_ID = 6053579919
SUPPORT_USERNAME = "@onedaytoalive"

# ============ Data Persistence (Upstash REST API) ============

USERS: dict[int, dict] = {}
SESSIONS: dict[int, dict] = {}

class UpstashRedisREST:
    def __init__(self, url: str, token: str):
        self.url = url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def get(self, key: str) -> str | None:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.url}/get/{key}", headers=self.headers)
                response.raise_for_status()
                result = response.json().get("result")
                return result
            except httpx.HTTPStatusError as e:
                logger.error(f"Upstash GET error for key '{key}': {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"Upstash GET failed for key '{key}': {e}")
                return None

    async def set(self, key: str, value: str):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.url}/set/{key}", headers=self.headers, data=value)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Upstash SET error for key '{key}': {e.response.text}")
            except Exception as e:
                logger.error(f"Upstash SET failed for key '{key}': {e}")

db_client = None

def get_db_client():
    global db_client
    if db_client is None:
        url = os.environ.get("UPSTASH_REDIS_REST_URL")
        token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if not url or not token:
            logger.error("Upstash environment variables not found.")
            return None
        db_client = UpstashRedisREST(url, token)
    return db_client

async def load_data():
    global USERS
    client = get_db_client()
    if not client:
        USERS = {}
        return
    try:
        data_str = await client.get("USERS")
        if data_str:
            USERS = {int(k): v for k, v in json.loads(data_str).items()}
        else:
            USERS = {}
    except Exception as e:
        logger.error(f"Failed to load user data from Upstash: {e}")
        USERS = {}

async def save_data():
    client = get_db_client()
    if not client:
        return
    try:
        await client.set("USERS", json.dumps(USERS))
    except Exception as e:
        logger.error(f"Failed to save user data to Upstash: {e}")

async def load_sessions():
    global SESSIONS
    client = get_db_client()
    if not client:
        SESSIONS = {}
        return
    try:
        data_str = await client.get("SESSIONS")
        if data_str:
            SESSIONS = {int(k): v for k, v in json.loads(data_str).items()}
        else:
            SESSIONS = {}
    except Exception as e:
        logger.error(f"Failed to load session data from Upstash: {e}")
        SESSIONS = {}

async def save_sessions():
    client = get_db_client()
    if not client:
        return
    try:
        await client.set("SESSIONS", json.dumps(SESSIONS))
    except Exception as e:
        logger.error(f"Failed to save session data to Upstash: {e}")


async def user(uid: int) -> dict:
    if uid not in USERS:
        USERS[uid] = { "packs": [], "current_pack": None, "daily_limit": 3, "ai_used": 0, "day_start": 0 }
        await save_data()
    return USERS[uid]

async def sess(uid: int) -> dict:
    if uid not in SESSIONS:
        SESSIONS[uid] = { "mode": "main", "sticker_data": {} }
        await save_sessions()
    return SESSIONS[uid]

async def reset_mode(uid: int):
    SESSIONS[uid] = { "mode": "main", "sticker_data": {} }
    await save_sessions()

# ============ Sticker Pack Management ============
async def get_user_packs(uid: int) -> list:
    u = await user(uid)
    return u.get("packs", [])

async def add_user_pack(uid: int, pack_name: str, pack_short_name: str):
    u = await user(uid)
    packs = u.get("packs", [])
    if not any(p['short_name'] == pack_short_name for p in packs):
        packs.append({"name": pack_name, "short_name": pack_short_name})
    u["packs"] = packs
    u["current_pack"] = pack_short_name
    await save_data()

async def set_current_pack(uid: int, pack_short_name: str):
    u = await user(uid)
    u["current_pack"] = pack_short_name
    await save_data()

from datetime import datetime, timezone

def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return int(midnight.timestamp())

async def _reset_daily_if_needed(u: dict):
    day_start = u.get("day_start", 0)
    today = _today_start_ts()
    if day_start < today:
        u["day_start"] = today
        u["ai_used"] = 0
        await save_data()

async def _quota_left(uid: int) -> int:
    u = await user(uid)
    await _reset_daily_if_needed(u)
    limit = u.get("daily_limit", 3)
    return max(0, limit - u.get("ai_used", 0))

async def _seconds_to_reset(uid: int) -> int:
    u = await user(uid)
    await _reset_daily_if_needed(u)
    now = int(datetime.now(timezone.utc).timestamp())
    end = u.get("day_start", 0) + 86400
    return max(0, end - now)

def _fmt_eta(secs: int) -> str:
    h = secs // 3600
    m = (secs % 3600) // 60
    if h <= 0 and m <= 0: return "کمتر از ۱ دقیقه"
    if h <= 0: return f"{m} دقیقه"
    if m == 0: return f"{h} ساعت"
    return f"{h} ساعت و {m} دقیقه"

CHANNEL_USERNAME = "@redoxbot_sticker"

async def require_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        pass

    keyboard = [
        [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")]
    ]

    text = f"برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید:\n{CHANNEL_USERNAME}"

    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return False


async def get_current_pack_short_name(uid: int) -> str | None:
    u = await user(uid)
    return u.get("current_pack")

async def check_pack_exists(bot, short_name: str) -> bool:
    try:
        await bot.get_sticker_set(name=short_name)
        return True
    except Exception:
        return False

def is_valid_pack_name(name: str) -> bool:
    if not (1 <= len(name) <= 50):
        return False
    if not name[0].isalpha():
        return False
    if name.endswith('_'):
        return False
    if '__' in name:
        return False
    for char in name:
        if not (char.isalnum() or char == '_'):
            return False
    return True

# ============ Font and Rendering Logic ============
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
LOCAL_FONT_FILES = {
    "Vazirmatn": "Vazirmatn-Regular.ttf",
    "Sahel": "Sahel.ttf",
    "IRANSans": "IRANSans.ttf",
    "Roboto": "Roboto-Regular.ttf",
    "Default": "Vazirmatn-Regular.ttf",
}

_LOCAL_FONTS = {
    key: os.path.join(FONT_DIR, path)
    for key, path in LOCAL_FONT_FILES.items()
    if os.path.isfile(os.path.join(FONT_DIR, path))
}

def _prepare_text(text: str) -> str:
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def resolve_font_path(font_key: str, text: str = "") -> str:
    return _LOCAL_FONTS.get(font_key, _LOCAL_FONTS.get("Default", ""))

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    size = base
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h:
            return size
        size -= 1
    return max(size, 12)

def _parse_hex(hx: str) -> tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3:
        r, g, b = [int(c * 2, 16) for c in hx]
    else:
        r = int(hx[0:2], 16)
        g = int(hx[2:4], 16)
        b = int(hx[4:6], 16)
    return (r, g, b, 255)

async def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str, bg_mode: str = "transparent", bg_photo: bytes | None = None, bg_photo_b64: str | None = None, as_webp: bool = False) -> bytes:
    W, H = (512, 512)

    photo_bytes = None
    if bg_photo_b64:
        try:
            photo_bytes = base64.b64decode(bg_photo_b64)
        except Exception:
            logger.error("Failed to decode base64 background image.")
    elif bg_photo: # For backward compatibility or other uses
        photo_bytes = bg_photo

    if photo_bytes:
        try:
            img = Image.open(io.BytesIO(photo_bytes)).convert("RGBA").resize((W, H))
        except Exception:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0) if bg_mode == "transparent" else (255, 255, 255, 255))

    draw = ImageDraw.Draw(img)
    color = _parse_hex(color_hex)
    padding = 40
    box_w, box_h = W - 2 * padding, H - 2 * padding
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)

    font_path = resolve_font_path(font_key, text)
    txt = _prepare_text(text)
    final_size = fit_font_size(draw, txt, font_path, base_size, box_w, box_h)

    try:
        font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), txt, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    if v_pos == "top": y = padding
    elif v_pos == "bottom": y = H - padding - text_height
    else: y = (H - text_height) / 2

    if h_pos == "left": x = padding
    elif h_pos == "right": x = W - padding - text_width
    else: x = W / 2

    draw.text((x, y), txt, font=font, fill=color, anchor="mm" if h_pos == "center" else "lm", stroke_width=2, stroke_fill=(0, 0, 0, 220))

    buf = io.BytesIO()
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

# ============ Bot Features Class ============
class TelegramBotFeatures:
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = """🎉 به ربات استیکر ساز خوش آمدید! 🎉

از منوی زیر یکی از گزینه‌ها را انتخاب کنید:
"""
        
        keyboard = [
            [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_creator"), InlineKeyboardButton("🗂 پک‌های من", callback_data="my_packs")],
            [InlineKeyboardButton("📊 سهمیه من", callback_data="my_quota"), InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
            [InlineKeyboardButton("📚 راهنما", callback_data="help")]
        ]
        if update.effective_user.id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton("👑 پنل ادمین", callback_data="admin:panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """📚 **راهنمای کامل ربات:**

🎨 **استیکر ساز:**
برای ساخت استیکر، از دکمه "استیکر ساز" در منوی اصلی استفاده کنید. شما باید یک پک استیکر بسازید یا یکی از پک‌های موجود خود را انتخاب کنید.

📞 **پشتیبانی:**
در صورت بروز مشکل، با پشتیبانی در تماس باشید.
"""
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(help_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(help_text, reply_markup=reply_markup)

bot_features = TelegramBotFeatures()

# Handler functions
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_channel_membership(update, context): return
    user_id = update.effective_user.id
    await reset_mode(user_id)
    await bot_features.start_command(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_channel_membership(update, context): return
    await bot_features.help_command(update, context)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data

    if callback_data == "check_membership":
        if await require_channel_membership(update, context):
            await query.message.delete()
            await bot_features.start_command(update, context)
        else:
            await query.answer("شما هنوز عضو کانال نیستید.", show_alert=True)
        return

    if not await require_channel_membership(update, context): return
    
    if callback_data == "back_to_main":
        await bot_features.start_command(update, context)
        return

    elif callback_data == "sticker_creator":
        packs = await get_user_packs(user_id)
        keyboard = [[InlineKeyboardButton(f"📦 {p['name']}", callback_data=f"pack:select:{p['short_name']}")] for p in packs]
        keyboard.append([InlineKeyboardButton("➕ ساخت پک جدید", callback_data="pack:new")])
        await query.edit_message_text(
            "یک پک استیکر را برای اضافه کردن انتخاب کنید، یا یک پک جدید بسازید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif callback_data.startswith("pack:select:"):
        pack_short_name = callback_data.split(":")[-1]
        await set_current_pack(user_id, pack_short_name)
        keyboard = [
            [InlineKeyboardButton("🖼 استیکر ساده", callback_data="sticker:simple")],
            [InlineKeyboardButton("✨ استیکر پیشرفته", callback_data="sticker:advanced")]
        ]
        await query.edit_message_text("نوع استیکر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif callback_data == "pack:new":
        current_sess = await sess(user_id)
        current_sess["mode"] = "pack_create_start"
        await save_sessions()
        await query.edit_message_text("""نام پک را بنویس (مثال: my_stickers):

• فقط حروف انگلیسی، عدد و آندرلاین (_)
• باید با حرف شروع شود
• نباید با آندرلاین (_) تمام شود
• نباید دو آندرلاین (__) پشت سر هم داشته باشد
• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)""")

    elif callback_data == "sticker:simple":
        current_sess = await sess(user_id)
        current_sess['sticker_mode'] = 'simple'
        current_sess['sticker_data'] = {
            "v_pos": "center", "h_pos": "center", "font_key": "Default",
            "color_hex": "#FFFFFF", "size_key": "medium", "bg_photo": None
        }
        await save_sessions()
        await query.edit_message_text("لطفاً متن استیکر ساده را ارسال کنید:")

    elif callback_data == "sticker:advanced":
        if user_id != ADMIN_ID and await _quota_left(user_id) <= 0:
            eta_str = _fmt_eta(await _seconds_to_reset(user_id))
            await query.answer(f"سهمیه شما تمام شده است. زمان بازنشانی: {eta_str}", show_alert=True)
            return
        current_sess = await sess(user_id)
        current_sess['sticker_mode'] = 'advanced'
        current_sess['sticker_data'] = {"v_pos": "center", "h_pos": "center", "font_key": "Default", "color_hex": "#FFFFFF", "size_key": "large", "bg_photo": None}
        await save_sessions()
        await query.edit_message_text("لطفاً متن استیکر پیشرفته را ارسال کنید:")

    elif callback_data.startswith("sticker_adv:"):
        parts = callback_data.split(':')
        action = parts[1]
        current_sess = await sess(user_id)
        sticker_data = current_sess.get('sticker_data', {})

        if action == 'custom_bg':
            choice = parts[2]
            if choice == 'yes':
                current_sess['mode'] = 'awaiting_custom_bg'
                await save_sessions()
                await query.edit_message_text("لطفاً عکس پس‌زمینه را ارسال کنید.")
            else:
                # If no custom bg, proceed based on sticker mode
                if current_sess.get("sticker_mode") == "simple":
                    # For simple stickers, this is the final step, show preview
                    preview_data = sticker_data.copy()
                    preview_text = preview_data.pop("text", "پیش‌نمایش")
                    defaults = { "v_pos": "center", "h_pos": "center", "font_key": "Default", "color_hex": "#FFFFFF", "size_key": "medium", "bg_photo": None }
                    defaults.update(preview_data)
                    img_bytes = await render_image(text=preview_text, **defaults, as_webp=False)
                    await query.message.reply_photo(photo=InputFile(img_bytes, filename="preview.png"), caption="این هم پیش‌نمایش. آیا تایید می‌کنید؟", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید", callback_data="sticker:confirm"), InlineKeyboardButton("✏️ ویرایش", callback_data="sticker:simple:edit")]]))
                else: # Advanced mode
                    keyboard = [[InlineKeyboardButton("بالا", callback_data="sticker_adv:vpos:top"), InlineKeyboardButton("وسط", callback_data="sticker_adv:vpos:center"), InlineKeyboardButton("پایین", callback_data="sticker_adv:vpos:bottom")]]
                    await query.edit_message_text("موقعیت عمودی متن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if action == 'vpos':
            sticker_data['v_pos'] = parts[2]
        elif action == 'hpos':
            sticker_data['h_pos'] = parts[2]
        elif action == 'color':
            sticker_data['color_hex'] = parts[2]
        elif action == 'size':
            sticker_data['size_key'] = parts[2]

        await save_sessions()

        # Determine next step
        if action == 'vpos':
            keyboard = [[InlineKeyboardButton("چپ", callback_data="sticker_adv:hpos:left"), InlineKeyboardButton("وسط", callback_data="sticker_adv:hpos:center"), InlineKeyboardButton("راست", callback_data="sticker_adv:hpos:right")]]
            await query.edit_message_text("موقعیت افقی متن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif action == 'hpos':
            keyboard = [[InlineKeyboardButton("سفید", callback_data="sticker_adv:color:#FFFFFF"), InlineKeyboardButton("مشکی", callback_data="sticker_adv:color:#000000")], [InlineKeyboardButton("قرمز", callback_data="sticker_adv:color:#F43F5E"), InlineKeyboardButton("آبی", callback_data="sticker_adv:color:#3B82F6")]]
            await query.edit_message_text("رنگ متن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif action == 'color':
            keyboard = [[InlineKeyboardButton("کوچک", callback_data="sticker_adv:size:small"), InlineKeyboardButton("متوسط", callback_data="sticker_adv:size:medium"), InlineKeyboardButton("بزرگ", callback_data="sticker_adv:size:large")]]
            await query.edit_message_text("اندازه فونت را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        elif action == 'size':
            preview_data = sticker_data.copy()
            preview_text = preview_data.pop("text", "پیش‌نمایش")
            # Ensure all keys are present for robustness
            defaults = {
                "v_pos": "center", "h_pos": "center", "font_key": "Default",
                "color_hex": "#FFFFFF", "size_key": "medium", "bg_photo": None
            }
            defaults.update(preview_data)
            img_bytes = await render_image(text=preview_text, **defaults)
            await query.message.reply_photo(photo=InputFile(img_bytes, filename="preview.png"), caption="این هم پیش‌نمایش. آیا تایید می‌کنید؟", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید", callback_data="sticker:confirm"), InlineKeyboardButton("✏️ ویرایش", callback_data="sticker:advanced:edit")]]))

    elif callback_data == "sticker:advanced:edit" or callback_data == "sticker:advanced:restart_edit":
        keyboard = [[InlineKeyboardButton("بالا", callback_data="sticker_adv:vpos:top"), InlineKeyboardButton("وسط", callback_data="sticker_adv:vpos:center"), InlineKeyboardButton("پایین", callback_data="sticker_adv:vpos:bottom")]]
        await query.edit_message_text("موقعیت عمودی متن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

import secrets

    elif callback_data == "sticker:confirm":
        # --- STAGE 1 of 2: Render and Upload ---
        await query.edit_message_caption("⏳ در حال پردازش و آپلود اولیه استیکر...", reply_markup=None)

        current_sess = await sess(user_id)
        sticker_data = current_sess.get('sticker_data', {})

        try:
            # Final render with safety defaults
            final_data = sticker_data.copy()
            final_text = final_data.pop("text", "")
            defaults = {
                "v_pos": "center", "h_pos": "center", "font_key": "Default",
                "color_hex": "#FFFFFF", "size_key": "medium", "bg_photo": None
            }
            defaults.update(final_data)

            img_bytes_png = await render_image(text=final_text, **defaults, as_webp=False)

            logger.info(f"Uploading sticker file for user {user_id} (Stage 1)...")
            uploaded_sticker = await context.bot.upload_sticker_file(user_id=user_id, sticker=InputFile(img_bytes_png, "sticker.png"), sticker_format="static")
            logger.info(f"Sticker file uploaded successfully. File ID: {uploaded_sticker.file_id}")

            # Generate a short, secure key to reference the file_id
            lookup_key = secrets.token_urlsafe(8)

            # Store the file_id in the session
            if 'pending_stickers' not in current_sess:
                current_sess['pending_stickers'] = {}
            current_sess['pending_stickers'][lookup_key] = uploaded_sticker.file_id
            await save_sessions()

            # Deduct quota now
            if current_sess.get("sticker_mode") == "advanced" and user_id != ADMIN_ID:
                u = await user(user_id)
                u["ai_used"] = u.get("ai_used", 0) + 1
                await save_data()

            # Now, send the confirmation message with the new button
            keyboard = [[InlineKeyboardButton("✅ افزودن به پک", callback_data=f"add_sticker:{lookup_key}")]]
            await query.message.reply_text(
                "✅ استیکر شما با موفقیت ساخته و آپلود شد!\n\n"
                "برای اضافه کردن نهایی به پک، دکمه زیر را فشار دهید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"STAGE 1 FAILED for user {user_id}: {e}", exc_info=True)
            await query.message.reply_text(f"خطا در مرحله اول ساخت استیکر: {e}")

    elif callback_data.startswith("add_sticker:"):
        # --- STAGE 2 of 2: Add to Set ---
        await query.edit_message_text("⏳ در حال اضافه کردن استیکر به پک...", reply_markup=None)

        lookup_key = callback_data.split(":")[-1]
        current_sess = await sess(user_id)

        # Retrieve the file_id from the session
        pending_stickers = current_sess.get('pending_stickers', {})
        file_id = pending_stickers.get(lookup_key)

        if not file_id:
            await query.message.reply_text("خطا: اطلاعات استیکر یافت نشد. ممکن است منقضی شده باشد. لطفاً دوباره تلاش کنید.")
            return

        pack_short_name = await get_current_pack_short_name(user_id)

        if not pack_short_name:
            await query.message.reply_text("خطا: پکی انتخاب نشده است. لطفاً دوباره شروع کنید.")
            return

        try:
            logger.info(f"Adding sticker to set {pack_short_name} for user {user_id} (Stage 2)...")
            await context.bot.add_sticker_to_set(user_id=user_id, name=pack_short_name, sticker=InputSticker(sticker=file_id, emoji_list=["😃"]))
            logger.info("Sticker added to set successfully.")

            pack_link = f"https://t.me/addstickers/{pack_short_name}"
            await query.message.reply_text(f"✅ استیکر شما با موفقیت به پک اضافه شد!\n\n{pack_link}")

            # Clean up the used key and reset user mode
            pending_stickers.pop(lookup_key, None)
            await save_sessions()
            await reset_mode(user_id)

        except Exception as e:
            logger.error(f"STAGE 2 FAILED for user {user_id}: {e}", exc_info=True)
            await query.message.reply_text(f"خطا در مرحله دوم افزودن استیکر: {e}")

    elif callback_data == "sticker:simple:edit":
        current_sess = await sess(user_id)
        current_sess['sticker_mode'] = 'simple'
        await save_sessions()
        await query.edit_message_text("لطفاً متن جدید استیکر ساده را ارسال کنید:")
    
    elif callback_data == "help":
        await bot_features.help_command(update, context)

    elif callback_data == "support":
        keyboard = [[InlineKeyboardButton("تماس با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]]
        await query.edit_message_text("برای تماس با پشتیبانی، از دکمه زیر استفاده کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif callback_data == "admin:panel":
        if user_id != ADMIN_ID: return
        keyboard = [[InlineKeyboardButton("ارسال پیام همگانی", callback_data="admin:broadcast_prompt")], [InlineKeyboardButton("ارسال پیام به کاربر", callback_data="admin:dm_prompt")], [InlineKeyboardButton("تغییر سهمیه کاربر", callback_data="admin:quota_prompt")]]
        await query.edit_message_text("👑 **پنل ادمین** 👑", reply_markup=InlineKeyboardMarkup(keyboard))

    elif callback_data.startswith("admin:"):
        action = callback_data.split(":")[1]
        if user_id != ADMIN_ID: return
        current_sess = await sess(user_id)
        if action == "broadcast_prompt":
            current_sess["mode"] = "admin_broadcast"
            await query.edit_message_text("پیام همگانی را ارسال کنید:")
        elif action == "dm_prompt":
            current_sess["mode"] = "admin_dm_id"
            await query.edit_message_text("آیدی عددی کاربر مورد نظر را ارسال کنید:")
        elif action == "quota_prompt":
            current_sess["mode"] = "admin_quota_id"
            await query.edit_message_text("آیدی عددی کاربر مورد نظر را ارسال کنید:")
        await save_sessions()

    elif callback_data.startswith("rate:"):
        await query.message.reply_text("از بازخورد شما متشکریم!")
        await reset_mode(user_id)
        await bot_features.start_command(update, context)

    elif callback_data == "my_quota":
        left = await _quota_left(user_id)
        total = (await user(user_id)).get("daily_limit", 3)
        eta_str = _fmt_eta(await _seconds_to_reset(user_id))
        text = f"📊 **سهمیه شما** 📊\n\nشما **{left}** از **{total}** سهمیه ساخت استیکر پیشرفته خود را باقی دارید.\n\nزمان بازنشانی بعدی: **{eta_str}**"
        await query.edit_message_text(text)

    elif callback_data == "my_packs":
        packs = await get_user_packs(user_id)
        if not packs:
            await query.edit_message_text("شما هنوز هیچ پکی نساخته‌اید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]))
            return
        message_text = "🗂 **پک‌های استیکر شما:**\n\n" + "\n".join([f"• <a href='https://t.me/addstickers/{p['short_name']}'>{p['name']}</a>" for p in packs])
        await query.edit_message_text(message_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]), disable_web_page_preview=True)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current_sess = await sess(user_id)
    if current_sess.get("mode") == "awaiting_custom_bg":
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        # Encode to Base64 to make it JSON serializable
        encoded_photo = base64.b64encode(bytes(photo_bytes)).decode('utf-8')

        sticker_data = current_sess.get("sticker_data", {})
        sticker_data["bg_photo_b64"] = encoded_photo # Store as a new key
        sticker_data.pop("bg_photo", None) # Remove old raw bytes key if it exists

        current_sess["mode"] = "main"
        await save_sessions()

        # After receiving photo, proceed based on sticker mode
        if current_sess.get("sticker_mode") == "simple":
            # For simple stickers, show preview immediately
            preview_data = sticker_data.copy()
            preview_text = preview_data.pop("text", "پیش‌نمایش")
            defaults = { "v_pos": "center", "h_pos": "center", "font_key": "Default", "color_hex": "#FFFFFF", "size_key": "medium" }
            defaults.update(preview_data)
            img_bytes = await render_image(text=preview_text, **defaults, as_webp=False)
            await update.message.reply_photo(photo=InputFile(img_bytes, filename="preview.png"), caption="این هم پیش‌نمایش. آیا تایید می‌کنید؟", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید", callback_data="sticker:confirm"), InlineKeyboardButton("✏️ ویرایش", callback_data="sticker:simple:edit")]]))
        else: # Advanced mode
            keyboard = [[InlineKeyboardButton("بالا", callback_data="sticker_adv:vpos:top"), InlineKeyboardButton("وسط", callback_data="sticker_adv:vpos:center"), InlineKeyboardButton("پایین", callback_data="sticker_adv:vpos:bottom")]]
            await update.message.reply_text("عکس پس‌زمینه دریافت شد. حالا موقعیت عمودی متن را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        await handle_photo(update, context)
        return

    user_id = update.effective_user.id
    text = update.message.text
    current_sess = await sess(user_id)
    current_mode = current_sess.get("mode")

    if user_id == ADMIN_ID:
        client = get_db_client()
        if current_mode == "admin_broadcast" and client:
            all_users_data = await client.get("USERS")
            if all_users_data:
                all_users = json.loads(all_users_data)
                for uid_str in all_users:
                    try: await context.bot.send_message(int(uid_str), text)
                    except Exception: pass
            await update.message.reply_text(f"پیام به {len(all_users)} کاربر ارسال شد.")
            await reset_mode(user_id)
            return
        elif current_mode == "admin_dm_id":
            current_sess["admin_target_id"] = int(text)
            current_sess["mode"] = "admin_dm_text"
            await save_sessions()
            await update.message.reply_text("پیام را برای ارسال بنویسید:")
            return
        elif current_mode == "admin_dm_text":
            target_id = current_sess.get("admin_target_id")
            try:
                await context.bot.send_message(target_id, text)
                await update.message.reply_text("پیام با موفقیت ارسال شد.")
            except Exception as e:
                await update.message.reply_text(f"خطا در ارسال پیام: {e}")
            await reset_mode(user_id)
            return
        elif current_mode == "admin_quota_id":
            current_sess["admin_target_id"] = int(text)
            current_sess["mode"] = "admin_quota_value"
            await save_sessions()
            await update.message.reply_text("مقدار سهمیه جدید را وارد کنید:")
            return
        elif current_mode == "admin_quota_value":
            target_id = current_sess.get("admin_target_id")
            target_user = await user(target_id)
            target_user["daily_limit"] = int(text)
            await save_data()
            await update.message.reply_text(f"سهمیه کاربر {target_id} به {text} تغییر یافت.")
            await reset_mode(user_id)
            return

    if current_mode == "pack_create_start":
        if not is_valid_pack_name(text):
            await update.message.reply_text("نام پک نامعتبر است. لطفاً دوباره تلاش کنید.")
            return

        bot_username = (await context.bot.get_me()).username
        pack_short_name = f"{text}_by_{bot_username}"

        if await check_pack_exists(context.bot, pack_short_name):
            await update.message.reply_text("این پک قبلاً وجود دارد. لطفاً یک نام دیگر انتخاب کنید.")
            return

        await update.message.reply_text("...لطفا کمی صبر کنید، پک استیکر شما در حال ساخته شدن است")
        dummy_sticker_bytes = await render_image("اولین", "center", "center", "Default", "#FFFFFF", "medium", as_webp=False)

        try:
            uploaded_sticker = await context.bot.upload_sticker_file(user_id=user_id, sticker=InputFile(dummy_sticker_bytes, "dummy.png"), sticker_format="static")
            await context.bot.create_new_sticker_set(user_id=user_id, name=pack_short_name, title=text, stickers=[InputSticker(sticker=uploaded_sticker.file_id, emoji_list=["🎉"])], sticker_format="static")
            await add_user_pack(user_id, text, pack_short_name)
            await set_current_pack(user_id, pack_short_name)

            keyboard = [[InlineKeyboardButton("🖼 استیکر ساده", callback_data="sticker:simple"), InlineKeyboardButton("✨ استیکر پیشرفته", callback_data="sticker:advanced")]]
            await context.bot.send_message(chat_id=user_id, text=f"پک «{text}» با موفقیت ساخته شد! حالا نوع استیکر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
            await reset_mode(user_id)
        except BadRequest as e:
            error_message = str(e)
            if "Sticker set name is already occupied" in error_message:
                await update.message.reply_text("این نام قبلاً گرفته شده است. لطفاً یک نام دیگر انتخاب کنید.")
            elif "Invalid sticker set name is specified" in error_message:
                await update.message.reply_text("""نامی که وارد کردید نامعتبر است. لطفاً دوباره وارد کنید.""")
            else:
                await update.message.reply_text(f"خطا در ساخت پک: {e}")
                await reset_mode(user_id)
        except Exception as e:
            await update.message.reply_text(f"یک خطای غیرمنتظره رخ داد: {e}")
            await reset_mode(user_id)
        return
    
    elif current_sess.get("sticker_mode") in ["simple", "advanced"]:
        sticker_data = current_sess.get("sticker_data", {})
        sticker_data["text"] = text
        current_sess["sticker_data"] = sticker_data
        await save_sessions()

        keyboard = [[InlineKeyboardButton("🏞 بله، عکس ارسال می‌کنم", callback_data="sticker_adv:custom_bg:yes")], [InlineKeyboardButton(" خیر، ادامه می‌دهم", callback_data="sticker_adv:custom_bg:no")]]
        await update.message.reply_text("آیا می‌خواهید از عکس دلخواه به عنوان پس‌زمینه استفاده کنید؟", reply_markup=InlineKeyboardMarkup(keyboard))

def setup_application(application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Vercel Serverless entry point
from flask import Flask, request, jsonify
app = Flask(__name__)

async def main_async():
    """The main asynchronous logic of the bot."""
    logger.info("Webhook received.")
    client = get_db_client()
    if not client:
        logger.error("Database client is not available.")
        # We cannot easily send a message back here, so we log and exit.
        return jsonify(status="error", message="Database not configured"), 500

    logger.info("Loading data and sessions...")
    await load_data()
    await load_sessions()
    logger.info("Data and sessions loaded.")

    TELEGRAM_TOKEN = os.getenv('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
    if not TELEGRAM_TOKEN:
        logger.error("No Telegram token found!")
        return jsonify(status="error", message="Bot token not configured"), 500

    logger.info("Building application...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    setup_application(application)
    logger.info("Application built.")

    try:
        logger.info("Initializing application...")
        await application.initialize()
        logger.info("Application initialized.")

        logger.info("Processing update...")
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        logger.info("Update processed.")

        logger.info("Shutting down application...")
        await application.shutdown()
        logger.info("Application shut down.")

        return jsonify(status="ok"), 200
    except Exception as e:
        logger.error(f"!!! CRITICAL ERROR processing webhook: {e}", exc_info=True)
        if 'application' in locals() and application.is_initialized:
            await application.shutdown()
        return jsonify(status="error", message=str(e)), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    This is the synchronous entry point for Vercel.
    It runs the main asynchronous logic using asyncio.run().
    """
    return asyncio.run(main_async())

@app.route('/')
def index():
    return "Bot is running!"

from telegram import Bot

