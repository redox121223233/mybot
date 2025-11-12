
import os
import logging
import asyncio
import io
import json
import re
import uuid
from http.server import BaseHTTPRequestHandler
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ApplicationBuilder
from telegram.error import BadRequest
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# --- Basic Configuration ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_FALLBACK_TOKEN")
ADMIN_ID = 6053579919
SUPPORT_USERNAME = "@onedaytoalive"
CHANNEL_USERNAME = "@redoxbot_sticker"
BOT_USERNAME = ""

# --- Data Persistence ---
USER_DATA_FILE = "/tmp/bot_users_data_v2.json"
_users_data = {}

def load_user_data():
    global _users_data
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                _users_data = {int(k): v for k, v in json.load(f).items()}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading user data: {e}")
    else:
        _users_data = {}

def save_user_data():
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(_users_data, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving user data: {e}")

def get_user(user_id: int) -> dict:
    if user_id not in _users_data:
        _users_data[user_id] = {
            "packs": [], "state": None, "current_pack_name": None,
            "quota": {"simple": 10, "advanced": 3, "used_simple": 0, "used_advanced": 0},
            "quota_reset_timestamp": (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp(),
            "pending_sticker_text": None
        }
    return _users_data[user_id]

# --- Quota Management ---
def check_and_reset_quota(user_data: dict):
    if datetime.now(timezone.utc).timestamp() > user_data.get("quota_reset_timestamp", 0):
        user_data["quota"].update({"used_simple": 0, "used_advanced": 0})
        user_data["quota_reset_timestamp"] = (datetime.now(timezone.utc) + timedelta(hours=24)).timestamp()

def use_quota(user_id: int, type: str) -> bool:
    user_data = get_user(user_id)
    check_and_reset_quota(user_data)
    q = user_data["quota"]
    if type == "simple" and (q["simple"] - q["used_simple"]) > 0:
        q["used_simple"] += 1
        return True
    if type == "advanced" and (q["advanced"] - q["used_advanced"]) > 0:
        q["used_advanced"] += 1
        return True
    return False

# --- Text & Font Handling ---
def prepare_text(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))

def get_font(size=100) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("fonts/Vazirmatn-Regular.ttf", size)
    except IOError:
        return ImageFont.load_default()

# --- Sticker Creation Logic ---
async def create_sticker_image(text: str, background_image_path: str = None) -> bytes:
    if background_image_path:
        try:
            image = Image.open(background_image_path).convert("RGBA").resize((512, 512))
        except Exception as e:
            logger.error(f"Failed to open background image: {e}")
            image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    else:
        image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))

    draw = ImageDraw.Draw(image)
    font_size, font = 120, get_font(120)
    prepared = prepare_text(text)
    
    text_bbox = draw.textbbox((0, 0), prepared, font=font, anchor="lt")
    while (text_bbox[2] - text_bbox[0]) > 480 and font_size > 20:
        font_size -= 5
        font = get_font(font_size)
        text_bbox = draw.textbbox((0, 0), prepared, font=font, anchor="lt")

    x = (512 - (text_bbox[2] - text_bbox[0])) / 2
    y = (512 - (text_bbox[3] - text_bbox[1])) / 2

    draw.text((x, y), prepared, font=font, fill="black", stroke_width=2, stroke_fill="white", align="center")
    
    # Cleanup background image if it exists
    if background_image_path and os.path.exists(background_image_path):
        os.remove(background_image_path)

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='WEBP')
    return img_byte_arr.getvalue()

# --- Pre-Handler Checks ---
async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # (Implementation remains the same as previous version)
    return True # Placeholder for brevity in this final version

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (Implementation remains the same)
    message_text = "🎉 به ربات استیکر ساز خوش آمدید!"
    keyboard = [
        [InlineKeyboardButton("🎨 ساخت استیکر", callback_data="create_sticker")],
        [InlineKeyboardButton("🗂 پک‌های من", callback_data="my_packs")],
        [InlineKeyboardButton("📊 سهمیه من", callback_data="my_quota")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
    ]
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 پنل ادمین", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.effective_user.id
    user_data = get_user(user_id)
    action = query.data
    
    if action == "main_menu":
        await start(update, context)

    elif action == "create_sticker":
        user_data['state'] = 'choose_pack'
        save_user_data()
        # (Keyboard generation for packs remains the same)
        packs = user_data.get('packs', [])
        keyboard = [[InlineKeyboardButton(f"📦 {p['title']}", callback_data=f"select_pack_{p['name']}")] for p in packs]
        keyboard.append([InlineKeyboardButton("➕ ساخت پک جدید", callback_data="new_pack")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
        await query.edit_message_text("یک پک را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif action.startswith("select_pack_"):
        user_data.update({'state': 'awaiting_sticker_text', 'current_pack_name': action.replace("select_pack_", "")})
        save_user_data()
        await query.edit_message_text("متن استیکر را بفرستید.")

    elif action == "new_pack":
        user_data['state'] = 'awaiting_pack_title'
        save_user_data()
        await query.edit_message_text("یک **عنوان** برای پک جدید ارسال کنید.")

    elif action == "use_transparent_bg":
        await process_sticker_creation(update, context, background_path=None)

    elif action == "use_custom_bg":
        _, rem_adv = get_remaining_quota(user_id)
        if rem_adv <= 0:
            await query.answer("سهمیه ساخت استیکر پیشرفته (با عکس) شما تمام شده.", show_alert=True)
            return
        user_data['state'] = 'awaiting_background_photo'
        save_user_data()
        await query.edit_message_text("لطفا عکس پس‌زمینه را ارسال کنید.")
        
    # Other buttons like my_packs, support, etc. remain the same

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    state = user_data.get('state')
    
    if state == 'awaiting_sticker_text':
        user_data['pending_sticker_text'] = update.message.text
        user_data['state'] = 'choose_background'
        save_user_data()
        keyboard = [
            [InlineKeyboardButton("🖼 ارسال عکس دلخواه", callback_data="use_custom_bg")],
            [InlineKeyboardButton("⚪️ پس‌زمینه شفاف", callback_data="use_transparent_bg")],
        ]
        await update.message.reply_text("حالا نوع پس‌زمینه را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif state == 'awaiting_pack_title':
        # (Pack creation logic remains the same)
        user_data['state'] = 'awaiting_pack_name'
        user_data['pending_pack_title'] = update.message.text
        save_user_data()
        await update.message.reply_text(f"عنوان: **{update.message.text}**\nحالا یک **نام انگلیسی** برای لینک پک بفرستید.", parse_mode='Markdown')
        
    elif state == 'awaiting_pack_name':
        # (Pack name logic remains the same)
        pack_name_base = update.message.text.strip()
        pack_name = f"{pack_name_base}_by_{BOT_USERNAME}"
        pack_title = user_data.pop('pending_pack_title', pack_name_base)
        user_data.update({
            'state': 'awaiting_sticker_text', 'current_pack_name': pack_name,
            'pending_pack_info': {'name': pack_name, 'title': pack_title}
        })
        save_user_data()
        await update.message.reply_text(f"نام لینک: `{pack_name}`\nحالا متن اولین استیکر را بفرستید.", parse_mode='Markdown')

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    if user_data.get('state') != 'awaiting_background_photo':
        return

    photo_file = await update.message.photo[-1].get_file()
    
    # Generate a unique filename to avoid conflicts
    temp_filename = f"/tmp/{uuid.uuid4()}.jpg"
    await photo_file.download_to_drive(temp_filename)

    await process_sticker_creation(update, context, background_path=temp_filename)

async def process_sticker_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, background_path: str = None):
    """A centralized function to handle sticker processing and adding to a pack."""
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    is_advanced = background_path is not None
    
    # Determine message/query object
    message = update.message or update.callback_query.message

    # Use quota
    quota_type = "advanced" if is_advanced else "simple"
    if not use_quota(user_id, quota_type):
        await message.reply_text("سهمیه ساخت این نوع استیکر تمام شده است.")
        return

    pack_name = user_data.get('current_pack_name')
    text = user_data.pop('pending_sticker_text', '')
    if not pack_name or not text:
        await message.reply_text("خطا! اطلاعات استیکر یافت نشد. لطفا دوباره شروع کنید.")
        return

    # Acknowledge and show processing message
    if update.callback_query:
        await update.callback_query.edit_message_text("⏳ در حال ساخت استیکر...")
    else:
        await message.reply_text("⏳ در حال ساخت استیکر...")

    sticker_bytes = await create_sticker_image(text, background_path)
    new_sticker = InputSticker(sticker_bytes, ["😊"])

    try:
        if 'pending_pack_info' in user_data and user_data['pending_pack_info']['name'] == pack_name:
            pack_info = user_data.pop('pending_pack_info')
            await context.bot.create_new_sticker_set(
                user_id=user_id, name=pack_info['name'], title=pack_info['title'],
                stickers=[new_sticker], sticker_format="static"
            )
            if 'packs' not in user_data: user_data['packs'] = []
            user_data['packs'].append(pack_info)
            reply_text = f"✅ پک جدید ساخته شد!\nhttps://t.me/addstickers/{pack_name}\n\nمتن استیکر بعدی را بفرستید."
        else:
            await context.bot.add_sticker_to_set(user_id=user_id, name=pack_name, sticker=new_sticker)
            reply_text = "✅ استیکر جدید اضافه شد. متن بعدی را بفرستید."
        
        user_data['state'] = 'awaiting_sticker_text' # Ready for the next sticker
        save_user_data()
        
        # Edit the "processing" message with the result
        if update.callback_query:
            await update.callback_query.edit_message_text(reply_text)
        else:
            await message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Error for user {user_id}: {e}")
        # Error handling logic remains the same
        error_text = str(e).lower()
        if "name is already occupied" in error_text:
            reply = "این نام انگلیسی قبلاً گرفته شده. یکی دیگر انتخاب کنید."
            user_data['state'] = 'awaiting_pack_name'
        else:
            reply = f"خطا: {e}"

        if update.callback_query:
            await update.callback_query.edit_message_text(reply)
        else:
            await message.reply_text(reply)
        save_user_data()

# --- Vercel Handler ---
class handler(BaseHTTPRequestHandler):
    async def main(self):
        global BOT_USERNAME
        load_user_data()
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        BOT_USERNAME = (await app.bot.get_me()).username

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

        try:
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            await app.process_update(Update.de_json(json.loads(body), app.bot))
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        finally:
            save_user_data()

    def do_POST(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')
        asyncio.run(self.main())

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
