import asyncio
import json
import logging
import os
import re
from io import BytesIO
from datetime import datetime, timezone

from flask import Flask, request as flask_request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext,
    ConversationHandler, CallbackQueryHandler
)
from telegram.error import BadRequest

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
from upstash_redis import Redis

# ================================== Logging ===================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================ Configuration ===============================
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5935332189"))
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@redoxbot_sticker")
DAILY_LIMIT = 5
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Vercel KV (Redis) Configuration
KV_URL = os.environ.get("KV_REST_API_URL")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN")

# ================================== Bot State =================================
bot_initialized = False
BOT_USERNAME = ""

# ================================== File Paths ================================
FONT_FILE = os.path.join(os.path.dirname(__file__), 'Vazirmatn-Regular.ttf')

# =========================== Data Management (Vercel KV) ========================
def get_redis_client():
    if not KV_URL or not KV_TOKEN:
        logger.error("Vercel KV environment variables (KV_REST_API_URL, KV_REST_API_TOKEN) are not set!")
        return None
    return Redis(url=KV_URL, token=KV_TOKEN)

redis = get_redis_client()

def get_user_data(uid: int) -> dict:
    if not redis: return {"packs": [], "daily_limit": DAILY_LIMIT, "ai_used": 0, "day_start": 0}
    key = f"user:{uid}"
    data = redis.get(key)
    return json.loads(data) if data else {"packs": [], "daily_limit": DAILY_LIMIT, "ai_used": 0, "day_start": 0}

def set_user_data(uid: int, data: dict):
    if not redis: return
    key = f"user:{uid}"
    redis.set(key, json.dumps(data))

def get_all_user_ids() -> list[int]:
    if not redis: return []
    keys = redis.keys("user:*")
    return [int(k.split(':')[1]) for k in keys]


def get_user(uid: int) -> dict:
    user_data = get_user_data(uid)
    now = datetime.now(timezone.utc)
    midnight = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())

    if user_data.get("day_start", 0) < midnight:
        user_data["day_start"] = midnight
        user_data["ai_used"] = 0
        set_user_data(uid, user_data)

    return user_data

# =============================== Render Functions =============================
def _prepare_text(text: str) -> str:
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    size = base
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size)
        except IOError:
            logger.error(f"Font not found at {font_path}, using default.")
            return 12
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h:
            return size
        size -= 2
    return size

def render_image(text: str, v_pos: str, h_pos: str, color_hex: str, size_key: str) -> bytes:
    W, H = (512, 512)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    padding = 40
    box_w, box_h = W - 2 * padding, H - 2 * padding
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)

    txt = _prepare_text(text)
    final_size = fit_font_size(draw, txt, FONT_FILE, base_size, box_w, box_h)
    font = ImageFont.truetype(FONT_FILE, size=final_size)

    bbox = draw.textbbox((0, 0), txt, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    y = (H - text_height) / 2
    if v_pos == "top": y = padding
    if v_pos == "bottom": y = H - padding - text_height

    x = (W - text_width) / 2
    if h_pos == "left": x = padding
    if h_pos == "right": x = W - padding - text_width

    stroke_fill = (0, 0, 0, 220)
    draw.text((x, y), txt, font=font, fill=color, stroke_width=2, stroke_fill=stroke_fill)

    buf = BytesIO()
    img.save(buf, format="WEBP")
    buf.seek(0)
    return buf.getvalue()

# ======================== Conversation States =======================
(MENU, PACK_NAME, PACK_TITLE, SIMPLE_TEXT, ADV_TEXT, ADV_VPOS, ADV_HPOS,
 ADV_COLOR, ADV_SIZE, ADMIN_PANEL, ADMIN_BROADCAST) = range(11)

# ============================ Keyboards ==============================
def main_menu_kb(is_admin: bool):
    keyboard = [
        [InlineKeyboardButton("استیکر ساده", callback_data="mode_simple")],
        [InlineKeyboardButton("استیکر پیشرفته", callback_data="mode_advanced")],
        [InlineKeyboardButton("سهمیه امروز", callback_data="quota")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("پنل ادمین", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

# ============================= Helpers ===============================
async def check_membership(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']: return True
    except Exception as e:
        logger.error(f"Error checking membership for {user_id}: {e}")

    url = f"https://t.me/{CHANNEL_ID.replace('@', '')}"
    await update.effective_message.reply_text(
        "برای استفاده از ربات، لطفا ابتدا در کانال ما عضو شوید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("عضویت در کانال", url=url)]])
    )
    return False

# ============================= Core Logic =================================
# --- Main Menu & Entry ---
async def start(update: Update, context: CallbackContext):
    if not await check_membership(update, context): return ConversationHandler.END
    is_admin = update.effective_user.id == ADMIN_ID
    await update.message.reply_text("سلام! به ربات استیکرساز خوش آمدید.", reply_markup=main_menu_kb(is_admin))
    return MENU

async def main_menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    is_admin = query.from_user.id == ADMIN_ID
    await query.edit_message_text("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
    context.user_data.clear()
    return MENU

# --- Features ---
async def quota_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_info = get_user(query.from_user.id)
    limit = user_info.get("daily_limit", DAILY_LIMIT)
    used = user_info.get("ai_used", 0)
    await query.message.reply_text(f"سهمیه شما: {limit - used}/{limit}")
    return MENU

# --- Sticker Pack Flow ---
async def choose_sticker_mode_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    mode = query.data.split('_')[1]
    context.user_data['mode'] = mode

    if mode == 'advanced':
        user_info = get_user(query.from_user.id)
        if query.from_user.id != ADMIN_ID and user_info['ai_used'] >= user_info['daily_limit']:
            await query.edit_message_text("سهمیه تمام شده.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="main_menu")]]))
            return MENU

    user_packs = get_user(query.from_user.id).get("packs", [])
    if not user_packs:
        await query.edit_message_text("شما پکی نساخته‌اید. لطفا نام انگلیسی برای پک جدید وارد کنید.")
        return PACK_NAME

    keyboard = [[InlineKeyboardButton(p['title'], callback_data=f"pack_{p['name']}")] for p in user_packs]
    keyboard.append([InlineKeyboardButton("➕ ساخت پک جدید", callback_data="pack_new")])
    await query.edit_message_text("کدام پک؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

async def select_pack_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    pack_name = query.data.split('_', 1)[1]
    context.user_data['pack_name'] = pack_name

    mode = context.user_data.get('mode')
    prompt = "متن استیکر ساده را بفرستید." if mode == 'simple' else "متن استیکر پیشرفته را بفرستید."
    next_state = SIMPLE_TEXT if mode == 'simple' else ADV_TEXT
    await query.edit_message_text(prompt)
    return next_state

async def new_pack_prompt_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("نام انگلیسی برای پک جدید وارد کنید (e.g., my_stickers).")
    return PACK_NAME

async def get_pack_name_handler(update: Update, context: CallbackContext):
    pack_name = update.message.text.strip()
    if not re.match("^[a-z0-9_]{1,50}$", pack_name):
        await update.message.reply_text("نام نامعتبر است. دوباره تلاش کنید.")
        return PACK_NAME

    global BOT_USERNAME
    if not BOT_USERNAME:
        bot_info = await context.bot.get_me()
        BOT_USERNAME = bot_info.username

    full_pack_name = f"{pack_name}_by_{BOT_USERNAME}"
    context.user_data['pack_name'] = full_pack_name
    await update.message.reply_text("یک عنوان برای پک انتخاب کنید.")
    return PACK_TITLE

async def get_pack_title_handler(update: Update, context: CallbackContext):
    pack_title = update.message.text.strip()
    pack_name = context.user_data['pack_name']
    user_id = update.effective_user.id

    dummy_sticker_bytes = render_image("اولین", "center", "center", "#FFFFFF", "medium")

    try:
        await context.bot.create_new_sticker_set(
            user_id=user_id, name=pack_name, title=pack_title,
            stickers=[InputSticker(sticker=dummy_sticker_bytes, emoji_list=["🎉"])],
            sticker_format='static'
        )
        user_info = get_user(user_id)
        user_info['packs'].append({'name': pack_name, 'title': pack_title})
        set_user_data(user_id, user_info)

        await update.message.reply_text(f"پک '{pack_title}' ساخته شد!")

        mode = context.user_data.get('mode')
        prompt = "حالا متن استیکر ساده را بفرستید." if mode == 'simple' else "حالا متن استیکر پیشرفته را بفرستید."
        next_state = SIMPLE_TEXT if mode == 'simple' else ADV_TEXT
        await update.message.reply_text(prompt)
        return next_state

    except BadRequest as e:
        await update.message.reply_text(f"خطا: {e.message}. نام دیگری انتخاب کنید.")
        return PACK_NAME

# --- Sticker Creation Flows ---
async def get_simple_text_handler(update: Update, context: CallbackContext):
    text = update.message.text
    pack_name = context.user_data['pack_name']
    sticker_bytes = render_image(text, "center", "center", "#FFFFFF", "large")

    try:
        await context.bot.add_sticker_to_set(
            user_id=update.effective_user.id, name=pack_name,
            sticker=InputSticker(sticker=sticker_bytes, emoji_list=["😃"])
        )
        await update.message.reply_text("استیکر اضافه شد!", reply_markup=main_menu_kb(update.effective_user.id == ADMIN_ID))
    except Exception as e:
        logger.error(f"Error adding simple sticker: {e}")
        await update.message.reply_text("خطا در افزودن استیکر.")

    context.user_data.clear()
    return MENU

async def get_adv_text_handler(update: Update, context: CallbackContext):
    context.user_data['text'] = update.message.text
    keyboard = [[InlineKeyboardButton(t, callback_data=f"vpos_{v}") for t, v in [("بالا", "top"), ("وسط", "center"), ("پایین", "bottom")]]]
    await update.message.reply_text("موقعیت عمودی:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADV_VPOS

async def get_adv_vpos_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['v_pos'] = query.data.split('_')[1]
    keyboard = [[InlineKeyboardButton(t, callback_data=f"hpos_{v}") for t, v in [("چپ", "left"), ("وسط", "center"), ("راست", "right")]]]
    await query.edit_message_text("موقعیت افقی:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADV_HPOS

async def get_adv_hpos_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['h_pos'] = query.data.split('_')[1]
    keyboard = [[InlineKeyboardButton(c, callback_data=f"color_{h}") for c, h in [("⬜️", "#FFFFFF"), ("⬛️", "#000000"), ("🟥", "#F43F5E"), ("🟦", "#3B82F6")]]]
    await query.edit_message_text("رنگ:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADV_COLOR

async def get_adv_color_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['color'] = query.data.split('_')[1]
    keyboard = [[InlineKeyboardButton(t, callback_data=f"size_{v}") for t, v in [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]]]
    await query.edit_message_text("اندازه:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADV_SIZE

async def get_adv_size_and_create_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['size'] = query.data.split('_')[1]

    ud = context.user_data
    sticker_bytes = render_image(ud['text'], ud['v_pos'], ud['h_pos'], ud['color'], ud['size'])

    try:
        await context.bot.add_sticker_to_set(
            user_id=query.from_user.id, name=ud['pack_name'],
            sticker=InputSticker(sticker=sticker_bytes, emoji_list=["😎"])
        )
        await query.edit_message_text("استیکر پیشرفته اضافه شد!", reply_markup=main_menu_kb(query.from_user.id == ADMIN_ID))

        if query.from_user.id != ADMIN_ID:
            user_info = get_user(query.from_user.id)
            user_info['ai_used'] += 1
            set_user_data(query.from_user.id, user_info)

    except Exception as e:
        logger.error(f"Error adding advanced sticker: {e}")
        await query.edit_message_text("خطا در افزودن استیکر.")

    context.user_data.clear()
    return MENU

# --- Admin Panel ---
async def admin_panel_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("شما ادمین نیستید.", show_alert=True)
        return MENU
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("ارسال پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("بازگشت", callback_data="main_menu")],
    ]
    await query.edit_message_text("پنل ادمین:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_PANEL

async def admin_broadcast_prompt_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("پیام خود را برای ارسال به همه کاربران بفرستید.")
    return ADMIN_BROADCAST

async def admin_broadcast_send_handler(update: Update, context: CallbackContext):
    message = update.message
    sent_count = 0
    user_ids = get_all_user_ids()
    for uid in user_ids:
        try:
            await context.bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.id)
            sent_count += 1
        except Exception as e:
            logger.warning(f"Could not broadcast to {uid}: {e}")

    await message.reply_text(f"پیام به {sent_count} کاربر از {len(user_ids)} کاربر ارسال شد.", reply_markup=main_menu_kb(True))
    return MENU

async def cancel_handler(update: Update, context: CallbackContext):
    await update.message.reply_text("لغو شد.", reply_markup=main_menu_kb(update.effective_user.id == ADMIN_ID))
    context.user_data.clear()
    return ConversationHandler.END

# ================================ Webhook Setup ===============================
async def post_init(application: Application):
    if not os.environ.get('VERCEL_URL'):
        logger.warning("VERCEL_URL not set, skipping webhook setup.")
        return
    webhook_url = f"https://{os.environ.get('VERCEL_URL')}/api/index"
    await application.bot.set_webhook(url=webhook_url, allowed_updates=Update.ALL_TYPES)
    logger.info(f"Webhook set to {webhook_url}")

app = Flask(__name__)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")
telegram_app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        MENU: [
            CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
            CallbackQueryHandler(quota_handler, pattern='^quota$'),
            CallbackQueryHandler(choose_sticker_mode_handler, pattern='^mode_'),
            CallbackQueryHandler(select_pack_handler, pattern='^pack_(?!new)'),
            CallbackQueryHandler(new_pack_prompt_handler, pattern='^pack_new$'),
            CallbackQueryHandler(admin_panel_handler, pattern='^admin_panel$'),
        ],
        PACK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pack_name_handler)],
        PACK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pack_title_handler)],
        SIMPLE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_simple_text_handler)],
        ADV_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_adv_text_handler)],
        ADV_VPOS: [CallbackQueryHandler(get_adv_vpos_handler, pattern='^vpos_')],
        ADV_HPOS: [CallbackQueryHandler(get_adv_hpos_handler, pattern='^hpos_')],
        ADV_COLOR: [CallbackQueryHandler(get_adv_color_handler, pattern='^color_')],
        ADV_SIZE: [CallbackQueryHandler(get_adv_size_and_create_handler, pattern='^size_')],
        ADMIN_PANEL: [
            CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
            CallbackQueryHandler(admin_broadcast_prompt_handler, pattern='^admin_broadcast$')
        ],
        ADMIN_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, admin_broadcast_send_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel_handler), CommandHandler('start', start)],
    per_message=False
)
telegram_app.add_handler(conv_handler)

@app.route('/api/index', methods=['POST'])
async def webhook():
    global bot_initialized
    if not bot_initialized:
        await telegram_app.initialize()
        bot_initialized = True

    update = Update.de_json(flask_request.get_json(force=True), telegram_app.bot)
    await telegram_app.process_update(update)
    return 'ok'
