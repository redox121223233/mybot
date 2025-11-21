#!/usr/bin/env python3
"""
Telegram Sticker Bot - Vercel Edition
"""
import os
import json
import logging
import asyncio
import io
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ==================== Basic Configuration ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 6053579919
CHANNEL_USERNAME = "@redoxbot_sticker"
SUPPORT_USERNAME = "@onedaytoalive"
DAILY_LIMIT = 5
FORBIDDEN_WORDS = ["kos", "kir", "kon", "koss", "kiri", "koon"]
telegram_app: Optional[Application] = None

# ==================== Data Persistence & State Management ====================
USERS_FILE, SESSIONS_FILE = "/tmp/users.json", "/tmp/sessions.json"

def _load_data(filename: str) -> Dict:
    try:
        with open(filename, 'r') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(filename, 'w') as f: json.dump({}, f)
        return {}

def _save_data(filename: str, data: Dict):
    with open(filename, 'w') as f: json.dump(data, f, indent=2)

def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    return int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())

def user(uid: int, full_data=False):
    users = _load_data(USERS_FILE)
    uid_str = str(uid)
    if uid_str not in users:
        users[uid_str] = {"ai_used": 0, "daily_limit": DAILY_LIMIT, "day_start": _today_start_ts(), "packs": [], "current_pack": None}
    if users[uid_str].get("day_start", 0) < _today_start_ts():
        users[uid_str]["day_start"] = _today_start_ts()
        users[uid_str]["ai_used"] = 0
    _save_data(USERS_FILE, users)
    return users if full_data else users[uid_str]

def sess(uid: int):
    return _load_data(SESSIONS_FILE).get(str(uid), {"mode": "menu", "data": {}})

def update_sess(uid: int, session_data: Dict):
    sessions = _load_data(SESSIONS_FILE)
    sessions[str(uid)] = session_data
    _save_data(SESSIONS_FILE, sessions)

def reset_mode(uid: int):
    update_sess(uid, {"mode": "menu", "data": {}})

# ==================== Keyboard Layouts ====================
def main_menu_kb(is_admin: bool = False):
    keyboard = [[InlineKeyboardButton("استیکر ساده", callback_data="menu:simple"), InlineKeyboardButton("استیکر پیشرفته", callback_data="menu:ai")],
                [InlineKeyboardButton("سهمیه امروز", callback_data="menu:quota"), InlineKeyboardButton("راهنما", callback_data="menu:help")],
                [InlineKeyboardButton("پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")]]
    if is_admin: keyboard.append([InlineKeyboardButton("پنل ادمین", callback_data="menu:admin")])
    return InlineKeyboardMarkup(keyboard)

def back_to_menu_kb(is_admin: bool = False):
    keyboard = [[InlineKeyboardButton("بازگشت به منو", callback_data="menu:home")]]
    if is_admin: keyboard[0].append(InlineKeyboardButton("پنل ادمین", callback_data="menu:admin"))
    return InlineKeyboardMarkup(keyboard)

def simple_bg_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("شفاف", callback_data="simple:bg:transparent"), InlineKeyboardButton("ارسال عکس", callback_data="simple:bg:photo_prompt")]])

def after_preview_kb(prefix: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید", callback_data=f"{prefix}:confirm"), InlineKeyboardButton("✏️ ویرایش", callback_data=f"{prefix}:edit")],
                                 [InlineKeyboardButton("بازگشت", callback_data="menu:home")]])

def pack_selection_kb(uid: int):
    keyboard, user_data = [], user(uid)
    packs = user_data.get("packs", [])
    current_pack_name = user_data.get("current_pack")
    current_pack = next((p for p in packs if p["short_name"] == current_pack_name), None)
    if current_pack: keyboard.append([InlineKeyboardButton(f"📦 {current_pack['name']} (فعلی)", callback_data=f"pack:select:{current_pack['short_name']}")])
    for p in packs:
        if not current_pack or p['short_name'] != current_pack['short_name']:
            keyboard.append([InlineKeyboardButton(f"📦 {p['name']}", callback_data=f"pack:select:{p['short_name']}")])
    keyboard.append([InlineKeyboardButton("➕ ساخت پک جدید", callback_data="pack:new")])
    return InlineKeyboardMarkup(keyboard)

def ai_vpos_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=f"ai:vpos:{v}") for t, v in [("🔺 بالا","top"),("↔️ وسط","center"),("🔻 پایین","bottom")]]])

def ai_hpos_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton(t, callback_data=f"ai:hpos:{v}") for t, v in [(" راست","right"),("وسط","center"),("چپ ","left")]]])

def color_palette_kb(prefix: str):
    colors = [("⚪️","#FFFFFF"),("⚫️","#000000"),("🔴","#F43F5E"),("🔵","#3B82F6"),("🟢","#22C55E"),("🟡","#EAB308"),("🟣","#8B5CF6"),("🟠","#F97316")]
    keyboard = [InlineKeyboardButton(t, callback_data=f"{prefix}:color:{h}") for t,h in colors]
    return InlineKeyboardMarkup([keyboard[i:i+4] for i in range(0, len(keyboard), 4)])

# ==================== Sticker Rendering Logic ====================
def _prepare_text(text: str) -> str:
    try: return get_display(arabic_reshaper.reshape(text))
    except: return text

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = (hx or "#ffffff").lstrip("#")
    return tuple(int(hx[i:i+2], 16) for i in (0, 2, 4)) + (255,)

def fit_font_size(draw, text, font_path, base_size, max_w, max_h):
    size = base_size
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size)
            bbox = draw.textbbox((0,0), text, font)
            if (bbox[2]-bbox[0]) <= max_w and (bbox[3]-bbox[1]) <= max_h: return size
        except IOError: return 32
        size -= 2
    return size

def render_image(data: Dict) -> bytes:
    W, H = (512, 512)
    bg_photo_hex = data.get("bg_photo")
    bg_photo = bytes.fromhex(bg_photo_hex) if bg_photo_hex else None
    img = Image.open(io.BytesIO(bg_photo)).convert("RGBA").resize((W,H)) if bg_photo else Image.new("RGBA",(W,H),(0,0,0,0))
    draw = ImageDraw.Draw(img)
    
    font_path, txt = "Vazirmatn-Regular.ttf", _prepare_text(data["text"])
    size_key = data.get("size", "medium")
    size_map = {"small":64,"medium":96,"large":128}
    size = fit_font_size(draw, txt, font_path, size_map[size_key], W-80, H-80)
    font = ImageFont.truetype(font_path, size=size)
    
    bbox = draw.textbbox((0,0), txt, font)
    v_pos = data.get("v_pos", "center")
    h_pos = data.get("h_pos", "center")
    y = 40 if v_pos=="top" else H-40-(bbox[3]-bbox[1]) if v_pos=="bottom" else (H-(bbox[3]-bbox[1]))/2
    anchor, x = "mm", W/2
    if h_pos == "left": anchor, x = "lm", 40
    elif h_pos == "right": anchor, x = "rm", W-40
    
    color = data.get("color", "#FFFFFF")
    draw.text((x,y), txt, font=font, fill=_parse_hex(color), anchor=anchor, stroke_width=2, stroke_fill=(0,0,0,180))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()

# ==================== Bot Handlers ====================
async def require_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'administrator', 'creator']: return True
    except BadRequest: pass
    
    kb = [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")], [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_membership")]]
    text = "👋 سلام! برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید و سپس روی «بررسی عضویت» کلیک کنید."
    if update.callback_query: await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await require_channel_membership(update, context):
        reset_mode(update.effective_user.id)
        await update.message.reply_text("سلام! به ربات استیکرساز خوش آمدید:", reply_markup=main_menu_kb(update.effective_user.id == ADMIN_ID))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query, user_id = update.callback_query, update.effective_user.id
    await query.answer()
    if query.data == "check_membership":
        if await require_channel_membership(update, context):
            await query.edit_message_text("✅ عضویت شما تایید شد!", reply_markup=main_menu_kb(user_id == ADMIN_ID))
        else:
            await query.answer("❗️ هنوز در کانال عضو نشده‌اید.", show_alert=True)
        return

    if not await require_channel_membership(update, context): return

    parts, s = query.data.split(":"), sess(user_id)
    mode, action = parts[0], parts[1]

    if mode == "menu":
        if action == "home": reset_mode(user_id); await query.edit_message_text("🏠 منوی اصلی:", reply_markup=main_menu_kb(user_id == ADMIN_ID))
        elif action in ["simple", "ai"]:
            s.update({"mode": action, "data": {"text": "", "v_pos": "center", "h_pos": "center", "color": "#FFFFFF", "size": "medium", "bg_photo": None}})
            update_sess(user_id, s)
            if not user(user_id)["packs"]:
                s["pack_wizard_mode"] = "awaiting_name"; update_sess(user_id, s)
                await query.edit_message_text("ابتدا باید یک پک بسازید. نام انگلیسی پک را بفرستید:", reply_markup=back_to_menu_kb(user_id == ADMIN_ID))
            else: await query.edit_message_text("استیکر را به کدام پک اضافه می‌کنید؟", reply_markup=pack_selection_kb(user_id))

    elif mode == "pack":
        if action == "new":
            s["pack_wizard_mode"] = "awaiting_name"; update_sess(user_id, s)
            await query.edit_message_text("نام انگلیسی پک را بفرستید (فقط حروف، تا ۲۰ کاراکтер):", reply_markup=back_to_menu_kb(user_id == ADMIN_ID))
        elif action == "select":
            users = user(user_id, True)
            users[str(user_id)]["current_pack"] = parts[2]
            _save_data(USERS_FILE, users)
            await query.edit_message_text(f"پک انتخاب شد. حالا متن استیکر را بفرستید.")

    elif mode in ["simple", "ai"]:
        s["data"][action] = parts[2]
        update_sess(user_id, s)
        next_steps = {"ai:vpos": ("موقعیت افقی:", ai_hpos_kb()), "ai:hpos": ("رنگ متن:", color_palette_kb("ai")),
                      "ai:color": ("اندازه فونت:", InlineKeyboardMarkup([[InlineKeyboardButton(l, callback_data=f"ai:size:{v}") for l,v in [("کوچک","small"),("متوسط","medium"),("بزرگ","large")]]]))}
        if f"{mode}:{action}" in next_steps:
            await query.edit_message_text(*next_steps[f"{mode}:{action}"])
        elif action == "confirm":
             try:
                sticker_bytes = render_image(s['data'])
                current_pack = user(user_id)["current_pack"]
                await context.bot.add_sticker_to_set(user_id=user_id, name=current_pack, sticker=InputSticker(sticker_bytes, ["😊"]))
                await query.edit_message_text(f"✅ استیکر به پک اضافه شد!\nhttps://t.me/addstickers/{current_pack}", reply_markup=main_menu_kb(user_id==ADMIN_ID))
                reset_mode(user_id)
             except Exception as e:
                await query.edit_message_text(f"⚠️ خطا در افزودن استیکر: {e}", reply_markup=back_to_menu_kb(user_id==ADMIN_ID))
        elif action == "edit":
            text = "متن را ارسال کنید:" if s["mode"] == "simple" else "موقعیت عمودی:"
            kb = None if s["mode"] == "simple" else ai_vpos_kb()
            await query.edit_message_text(text, reply_markup=kb)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, text = update.effective_user.id, update.message.text
    s = sess(user_id)

    if s.get("pack_wizard_mode") == "awaiting_name":
        pack_name = text.strip()
        if any(w in pack_name.lower() for w in FORBIDDEN_WORDS) or not pack_name.isalpha() or len(pack_name) > 20:
            await update.message.reply_text("نام نامعتبر است. لطفاً دوباره تلاش کنید.", reply_markup=back_to_menu_kb(user_id==ADMIN_ID))
            return

        bot_username = (await context.bot.get_me()).username
        pack_short_name = f"{pack_name}_by_{bot_username}"

        try:
            dummy_sticker = render_image({"text":"سلام!", "v_pos":"center", "h_pos":"center", "color":"#FFFFFF", "size":"medium"})
            await context.bot.create_new_sticker_set(user_id, pack_short_name, f"{pack_name} by @{bot_username}", [InputSticker(dummy_sticker, ["👋"])], "static")
            
            users = user(user_id, True)
            user_data = users[str(user_id)]
            user_data["packs"].append({"name": pack_name, "short_name": pack_short_name})
            user_data["current_pack"] = pack_short_name
            _save_data(USERS_FILE, users)
            
            s.pop("pack_wizard_mode"); update_sess(user_id, s)
            await update.message.reply_text(f"✅ پک «{pack_name}» ساخته شد. حالا متن استیکر را بفرستید.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ خطا در ساخت پک: {e}", reply_markup=back_to_menu_kb(user_id==ADMIN_ID))
    
    elif s.get("mode") in ["simple", "ai"]:
        s["data"]["text"] = text
        update_sess(user_id, s)
        await update.message.reply_photo(render_image(s["data"]), caption="پیش‌نمایش استیکر:", reply_markup=after_preview_kb(s["mode"]))

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, s = update.effective_user.id, sess(user_id)
    if s.get("mode") in ["simple", "ai"]:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        s["data"]["bg_photo"] = (await file.download_as_bytearray()).hex()
        update_sess(user_id, s)
        await update.message.reply_text("✅ عکس پس‌زمینه تنظیم شد. حالا متن را بفرستید.")

# ==================== App Setup & Webhook ====================
async def setup_telegram_app():
    """Initializes the Telegram bot application and its handlers."""
    global telegram_app
    if BOT_TOKEN:
        telegram_app = Application.builder().token(BOT_TOKEN).build()
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CallbackQueryHandler(button_handler))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        await telegram_app.initialize()

# Initialize the bot
if BOT_TOKEN:
    asyncio.run(setup_telegram_app())

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Webhook endpoint to process updates from Telegram."""
    if telegram_app:
        update_data = request.get_json()
        await telegram_app.process_update(Update.de_json(update_data, telegram_app.bot))
    return "OK", 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint for Vercel."""
    return jsonify({"status": "healthy"})
