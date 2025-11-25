import logging
import os
import re
from io import BytesIO
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext,
    ConversationHandler, CallbackQueryHandler, ApplicationBuilder
)
from telegram.error import BadRequest
from telegram.request import Request as TelegramRequest

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ================================== Logging ===================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================ Configuration ===============================
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5935332189"))
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@redoxbot_sticker")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DAILY_LIMIT = 5

# =========================== In-Memory Storage ==============================
user_data_in_memory = {}

def get_user(uid: int) -> dict:
    if uid not in user_data_in_memory:
        user_data_in_memory[uid] = {"packs": [], "daily_limit": DAILY_LIMIT, "ai_used": 0, "day_start": 0}

    user = user_data_in_memory[uid]
    now = datetime.now(timezone.utc)
    midnight = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())

    if user.get("day_start", 0) < midnight:
        user["day_start"] = midnight
        user["ai_used"] = 0

    return user

# ================================== Bot State =================================
BOT_USERNAME = ""

# ================================== File Paths ================================
FONT_FILE = os.path.join(os.path.dirname(__file__), 'fonts', 'Vazirmatn-Regular.ttf')

# =============================== Render Functions =============================
def _prepare_text(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))

def render_image(text, v_pos, h_pos, color_hex, size_key):
    W, H = 512, 512
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    padding, size_map = 40, {"small": 64, "medium": 96, "large": 128}
    box_w, box_h = W - 2 * padding, H - 2 * padding

    txt = _prepare_text(text)

    font_size = size_map.get(size_key, 96)
    try:
        font = ImageFont.truetype(FONT_FILE, size=font_size)
    except IOError:
        font = ImageFont.load_default()
        logger.warning(f"Font file not found at {FONT_FILE}")

    bbox = draw.textbbox((0, 0), txt, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    y = (H - th) / 2
    if v_pos == "top": y = padding
    if v_pos == "bottom": y = H - padding - th
    x = (W - tw) / 2
    if h_pos == "left": x = padding
    if h_pos == "right": x = W - padding - tw

    draw.text((x, y), txt, font=font, fill=color, stroke_width=2, stroke_fill=(0,0,0,220))

    buf = BytesIO()
    img.save(buf, format="WEBP")
    buf.seek(0)
    return buf.getvalue()

# ======================== Conversation States =======================
(MENU, PACK_NAME, PACK_TITLE, STICKER_TEXT, STICKER_VPOS, STICKER_HPOS,
 STICKER_COLOR, STICKER_SIZE, ADMIN_PANEL, ADMIN_BROADCAST) = range(10)

# ============================ Keyboards ==============================
def main_menu_kb(is_admin: bool):
    keyboard = [
        [InlineKeyboardButton("ساخت استیکر", callback_data="create_sticker")],
        [InlineKeyboardButton("سهمیه روزانه", callback_data="quota")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("پنل ادمین", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

# ============================= Helpers ===============================
async def check_membership(update, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, update.effective_user.id)
        if member.status in ['member', 'administrator', 'creator']: return True
    except Exception as e:
        logger.error(f"Membership check failed: {e}")
    url = f"https://t.me/{CHANNEL_ID.replace('@', '')}"
    await update.effective_message.reply_text("برای استفاده از ربات، لطفا در کانال عضو شوید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("عضویت", url=url)]]))
    return False

# ============================= Core Logic =================================
async def start(update: Update, context: CallbackContext):
    if not await check_membership(update, context): return ConversationHandler.END
    is_admin = update.effective_user.id == ADMIN_ID
    get_user(update.effective_user.id)
    await update.message.reply_text("سلام! به ربات استیکرساز خوش آمدید.", reply_markup=main_menu_kb(is_admin))
    return MENU

async def main_menu_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    is_admin = query.from_user.id == ADMIN_ID
    await query.edit_message_text("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
    context.user_data.clear()
    return MENU

async def quota_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    await query.message.reply_text(f"سهمیه شما: {user['daily_limit'] - user['ai_used']}/{user['daily_limit']}")
    return MENU

async def create_sticker_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user = get_user(query.from_user.id)
    if query.from_user.id != ADMIN_ID and user['ai_used'] >= user['daily_limit']:
        await query.edit_message_text("سهمیه شما تمام شده است.")
        return MENU

    await query.edit_message_text("نام انگلیسی برای پک استیکر وارد کنید.")
    return PACK_NAME

async def get_pack_name_handler(update: Update, context: CallbackContext):
    pack_name = update.message.text.strip()
    if not re.match("^[a-z0-9_]{1,50}$", pack_name):
        await update.message.reply_text("نام نامعتبر است.")
        return PACK_NAME

    global BOT_USERNAME
    if not BOT_USERNAME: BOT_USERNAME = (await context.bot.get_me()).username

    context.user_data['pack_name'] = f"{pack_name}_by_{BOT_USERNAME}"
    await update.message.reply_text("یک عنوان برای پک انتخاب کنید.")
    return PACK_TITLE

async def get_pack_title_handler(update: Update, context: CallbackContext):
    pack_title = update.message.text.strip()
    pack_name = context.user_data['pack_name']

    try:
        await context.bot.create_new_sticker_set(
            user_id=update.effective_user.id, name=pack_name, title=pack_title,
            stickers=[InputSticker(sticker=render_image("اولین", "center", "center", "#FFFFFF", "medium"), emoji_list=["🎉"])],
            sticker_format='static'
        )
        pack_link = f"https://t.me/addstickers/{pack_name}"
        await update.message.reply_text(f"پک '{pack_title}' ساخته شد!\\n\\nمهم: لینک را ذخیره کنید چون ربات حافظه دائمی ندارد:\\n{pack_link}")
        await update.message.reply_text("متن استیکر بعدی را بفرستید.")
        return STICKER_TEXT
    except BadRequest as e:
        await update.message.reply_text(f"خطا: {e.message}. نام دیگری انتخاب کنید.")
        return PACK_NAME

async def get_sticker_text_handler(update: Update, context: CallbackContext):
    context.user_data['text'] = update.message.text
    keyboard = [[InlineKeyboardButton(t, callback_data=f"vpos_{v}") for t,v in [("بالا","top"),("وسط","center"),("پایین","bottom")]]]
    await update.message.reply_text("موقعیت عمودی:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STICKER_VPOS

# ... (the rest of the handlers would be here, following the same pattern)
async def get_sticker_vpos_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['v_pos'] = query.data.split('_')[1]
    keyboard = [[InlineKeyboardButton(t, callback_data=f"hpos_{v}") for t,v in [("چپ","left"),("وسط","center"),("راست","right")]]]
    await query.edit_message_text("موقعیت افقی:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STICKER_HPOS

async def get_sticker_hpos_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['h_pos'] = query.data.split('_')[1]
    keyboard = [[InlineKeyboardButton(c, callback_data=f"color_{h}") for c,h in [("⬜️","#FFFFFF"),("⬛️","#000000"),("🟥","#F43F5E"),("🟦","#3B82F6")]]]
    await query.edit_message_text("رنگ:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STICKER_COLOR

async def get_sticker_color_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['color'] = query.data.split('_')[1]
    keyboard = [[InlineKeyboardButton(t, callback_data=f"size_{v}") for t,v in [("کوچک","small"),("متوسط","medium"),("بزرگ","large")]]]
    await query.edit_message_text("اندازه:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STICKER_SIZE

async def get_sticker_size_and_create_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    context.user_data['size'] = query.data.split('_')[1]
    ud = context.user_data

    try:
        sticker_bytes = render_image(ud['text'], ud['v_pos'], ud['h_pos'], ud['color'], ud['size'])
        await context.bot.add_sticker_to_set(
            user_id=query.from_user.id, name=ud['pack_name'],
            sticker=InputSticker(sticker=sticker_bytes, emoji_list=["😎"])
        )
        await query.edit_message_text("استیکر اضافه شد! متن بعدی را بفرستید یا با /cancel لغو کنید.")
        if query.from_user.id != ADMIN_ID:
            get_user(query.from_user.id)['ai_used'] += 1
        return STICKER_TEXT
    except Exception as e:
        await query.edit_message_text(f"خطا در افزودن استیکر: {e}. با /start مجددا تلاش کنید.")
        return ConversationHandler.END

async def admin_panel_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("ارسال پیام همگانی", callback_data="admin_broadcast")],
                [InlineKeyboardButton("بازگشت", callback_data="main_menu")]]
    await query.edit_message_text("پنل ادمین:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_PANEL

async def admin_broadcast_prompt_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("پیام برای ارسال به همه کاربران را بفرستید.")
    return ADMIN_BROADCAST

async def admin_broadcast_send_handler(update: Update, context: CallbackContext):
    sent_count = 0
    for uid in user_data_in_memory.keys():
        try:
            await context.bot.copy_message(uid, update.message.chat.id, update.message.id)
            sent_count += 1
        except Exception as e:
            logger.warning(f"Broadcast failed for {uid}: {e}")
    await update.message.reply_text(f"پیام به {sent_count} کاربر ارسال شد.", reply_markup=main_menu_kb(True))
    return MENU

async def cancel_handler(update: Update, context: CallbackContext):
    await update.message.reply_text("عملیات لغو شد.", reply_markup=main_menu_kb(update.effective_user.id == ADMIN_ID))
    context.user_data.clear()
    return ConversationHandler.END


def build_application():
    # Configure custom request object with increased timeouts
    request = TelegramRequest(connect_timeout=30.0, read_timeout=30.0)
    application = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MENU: [
                CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
                CallbackQueryHandler(quota_handler, pattern='^quota$'),
                CallbackQueryHandler(create_sticker_handler, pattern='^create_sticker$'),
                CallbackQueryHandler(admin_panel_handler, pattern='^admin_panel$'),
            ],
            PACK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pack_name_handler)],
            PACK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pack_title_handler)],
            STICKER_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_sticker_text_handler)],
            STICKER_VPOS: [CallbackQueryHandler(get_sticker_vpos_handler, pattern='^vpos_')],
            STICKER_HPOS: [CallbackQueryHandler(get_sticker_hpos_handler, pattern='^hpos_')],
            STICKER_COLOR: [CallbackQueryHandler(get_sticker_color_handler, pattern='^color_')],
            STICKER_SIZE: [CallbackQueryHandler(get_sticker_size_and_create_handler, pattern='^size_')],
            ADMIN_PANEL: [
                CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
                CallbackQueryHandler(admin_broadcast_prompt_handler, pattern='^admin_broadcast$')
            ],
            ADMIN_BROADCAST: [MessageHandler(filters.ALL & ~filters.COMMAND, admin_broadcast_send_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel_handler)],
        per_message=False
    )
    application.add_handler(conv_handler)
    return application
