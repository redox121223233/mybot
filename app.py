#!/usr/bin/env python3
"""
Telegram Sticker Bot - Railway/Render Compatible Version
Optimized for non-Vercel deployment with proper webhook handling
"""
import os
import json
import logging
import asyncio
import io
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import arabic_reshaper
from bidi.algorithm import get_display

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
PORT = int(os.getenv('PORT', 5000))
ADMIN_ID = 6053579919  # Make sure this is your admin ID
CHANNEL_USERNAME = "@redoxbot_sticker"  # Your channel username
SUPPORT_USERNAME = "@onedaytoalive"
DAILY_LIMIT = 5
FORBIDDEN_WORDS = ["kos", "kir", "kon", "koss", "kiri", "koon"]


# Global application
telegram_app = None

# ==================== Data Persistence ====================
def _load_data(filename: str) -> Dict:
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _save_data(filename: str, data: Dict):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

USERS_FILE = "/tmp/users.json"
SESSIONS_FILE = "/tmp/sessions.json"

# ==================== Session and User Management ====================

def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return int(midnight.timestamp())

def user(uid: int) -> Dict[str, Any]:
    users = _load_data(USERS_FILE)
    uid_str = str(uid)
    
    if uid_str not in users:
        users[uid_str] = {
            "ai_used": 0,
            "daily_limit": DAILY_LIMIT,
            "day_start": _today_start_ts(),
            "packs": [],
            "current_pack": None
        }
    
    # Reset daily limit if a new day has started
    if users[uid_str].get("day_start", 0) < _today_start_ts():
        users[uid_str]["day_start"] = _today_start_ts()
        users[uid_str]["ai_used"] = 0
    
    _save_data(USERS_FILE, users)
    return users[uid_str]

def sess(uid: int) -> Dict[str, Any]:
    sessions = _load_data(SESSIONS_FILE)
    uid_str = str(uid)
    
    if uid_str not in sessions:
        sessions[uid_str] = {"mode": "menu", "data": {}}
        _save_data(SESSIONS_FILE, sessions)

    return sessions[uid_str]

def update_sess(uid: int, session_data: Dict):
    sessions = _load_data(SESSIONS_FILE)
    sessions[str(uid)] = session_data
    _save_data(SESSIONS_FILE, sessions)

def reset_mode(uid: int):
    update_sess(uid, {"mode": "menu", "data": {}})

def get_user_packages(user_id: int) -> list:
    """Get user's sticker packages"""
    return user(user_id).get("packs", [])

def add_user_pack(uid: int, pack_name: str, pack_short_name: str):
    """Adds a new sticker pack to the user's list."""
    users = _load_data(USERS_FILE)
    uid_str = str(uid)
    user_data = users.get(uid_str, {})
    
    packs = user_data.get("packs", [])
    if not any(p["short_name"] == pack_short_name for p in packs):
        packs.append({"name": pack_name, "short_name": pack_short_name})
    
    user_data["packs"] = packs
    user_data["current_pack"] = pack_short_name
    users[uid_str] = user_data
    _save_data(USERS_FILE, users)

def get_current_pack(uid: int) -> Optional[Dict[str, str]]:
    """Gets the user's currently selected sticker pack."""
    user_data = user(uid) # Ensures user exists and is up-to-date
    current_pack_short_name = user_data.get("current_pack")
    if current_pack_short_name:
        for pack in user_data.get("packs", []):
            if pack["short_name"] == current_pack_short_name:
                return pack
    return None

# ==================== Channel Membership ====================

async def check_channel_membership(bot, user_id: int) -> bool:
    """Check if a user is a member of the channel."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking channel membership for {user_id}: {e}")
        return False

async def require_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Send a message if the user is not in the channel."""
    user_id = update.effective_user.id
    if await check_channel_membership(context.bot, user_id):
        return True

    keyboard = [
        [InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("بررسی عضویت", callback_data="check_membership")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.\n\n"
        "پس از عضویت، روی دکمه «بررسی عضویت» کلیک کنید.",
        reply_markup=reply_markup
    )
    return False

# ==================== Sticker Rendering ====================

def _prepare_text(text: str) -> str:
    """Reshape and apply bidi algorithm for Persian text."""
    if not text:
        return ""
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception:
        return text

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    """Parse hex color string to RGBA tuple."""
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3:
        r, g, b = [int(c * 2, 16) for c in hx]
    else:
        r, g, b = [int(hx[i:i+2], 16) for i in (0, 2, 4)]
    return (r, g, b, 255)

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    """Find the best font size to fit text within a box."""
    size = base
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size)
        except IOError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h:
            return size
        size -= 2
    return max(size, 12)

def render_image(text: str, v_pos: str, h_pos: str, color_hex: str, size_key: str,
                bg_mode: str = "transparent", bg_photo: Optional[bytes] = None) -> bytes:
    """Render a sticker image from text and parameters."""
    W, H = (512, 512)
    
    if bg_photo:
        try:
            img = Image.open(io.BytesIO(bg_photo)).convert("RGBA").resize((W, H))
        except Exception:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    elif bg_mode == "default":
        img = Image.new("RGBA", (W, H), (20, 20, 35, 255)) # Default dark background
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)
    color = _parse_hex(color_hex)
    padding = 40
    box_w, box_h = W - 2 * padding, H - 2 * padding
    
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)

    font_path = "Vazirmatn-Regular.ttf"
    txt = _prepare_text(text)
    final_size = fit_font_size(draw, txt, font_path, base_size, box_w, box_h)
    
    try:
        font = ImageFont.truetype(font_path, size=final_size)
    except IOError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), txt, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    y = (H - text_height) / 2
    if v_pos == "top":
        y = padding
    elif v_pos == "bottom":
        y = H - padding - text_height

    x = W / 2
    anchor = "mm"
    if h_pos == "left":
        x = padding
        anchor = "lm"
    elif h_pos == "right":
        x = W - padding - text_width
        anchor = "rm"

    draw.text(
        (x, y),
        txt,
        font=font,
        fill=color,
        anchor=anchor,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 180)
    )

    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()

def image_to_webp_bytes(img: Image.Image) -> bytes:
    """Convert PIL Image to WebP bytes"""
    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=95, method=6)
    return buffer.getvalue()

# ==================== Keyboard Layouts ====================

def main_menu_kb(is_admin: bool = False):
    keyboard = [
        [InlineKeyboardButton("استیکر ساده", callback_data="menu:simple"), InlineKeyboardButton("استیکر پیشرفته", callback_data="menu:ai")],
        [InlineKeyboardButton("سهمیه امروز", callback_data="menu:quota"), InlineKeyboardButton("راهنما", callback_data="menu:help")],
        [InlineKeyboardButton("پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("پنل ادمین", callback_data="menu:admin")])
    return InlineKeyboardMarkup(keyboard)

def back_to_menu_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت به منو", callback_data="menu:home")]])

def pack_selection_kb(uid: int):
    """Generates a keyboard for selecting a sticker pack."""
    keyboard = []
    user_packs = get_user_packs(uid)
    current_pack = get_current_pack(uid)

    if current_pack:
        keyboard.append([InlineKeyboardButton(f"📦 {current_pack['name']} (فعلی)", callback_data=f"pack:select:{current_pack['short_name']}")])

    for pack in user_packs:
        if not current_pack or pack['short_name'] != current_pack['short_name']:
            keyboard.append([InlineKeyboardButton(f"📦 {pack['name']}", callback_data=f"pack:select:{pack['short_name']}")])

    keyboard.append([InlineKeyboardButton("➕ ساخت پک جدید", callback_data="pack:new")])
    return InlineKeyboardMarkup(keyboard)

# ==================== Bot Command Handlers ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    if not await require_channel_membership(update, context):
        return

    reset_mode(user_id)
    is_admin = (user_id == ADMIN_ID)
    
    await update.message.reply_text(
        "سلام! به ربات استیکرساز خوش آمدید.\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu_kb(is_admin)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "راهنما\n\n"
        "• استیکر ساده: ساخت استیکر با تنظیمات سریع\n"
        "• استیکر ساز پیشرفته: ساخت استیکر با تنظیمات پیشرفته\n"
        "• سهمیه امروز: محدودیت استفاده روزانه\n"
        "• پشتیبانی: ارتباط با ادمین"
    )
    await update.message.reply_text(help_text, reply_markup=back_to_menu_kb())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    is_admin = (user_id == ADMIN_ID)

    # Check for channel membership first
    if query.data != "check_membership":
        is_member = await check_channel_membership(context.bot, user_id)
        if not is_member:
            await query.edit_message_text(
                f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"),
                    InlineKeyboardButton("بررسی عضویت", callback_data="check_membership")
                ]])
            )
            return

    parts = query.data.split(":")
    mode = parts[0]

    if mode == "menu":
        action = parts[1]
        if action == "home":
            reset_mode(user_id)
            await query.edit_message_text(
                "منوی اصلی:",
                reply_markup=main_menu_kb(is_admin)
            )
        elif action == "help":
            await query.edit_message_text(
                "راهنما:\n\n"
                "• استیکر ساده: ساخت استیکر با تنظیمات سریع\n"
                "• استیکر پیشرفته: ساخت استیکر با تنظیمات پیشرفته\n"
                "• سهمیه امروز: محدودیت استفاده روزانه\n",
                reply_markup=back_to_menu_kb()
            )
        elif action == "quota":
            u = user(user_id)
            left = "نامحدود" if is_admin else f'{max(0, u["daily_limit"] - u["ai_used"])} از {u["daily_limit"]}'
            await query.edit_message_text(
                f"سهمیه امروز شما برای استیکر پیشرفته: {left}",
                reply_markup=back_to_menu_kb()
            )
        elif action in ["simple", "ai"]:
            s = sess(user_id)
            s["mode"] = action
            s["data"] = {} # Reset data for new creation

            # Check daily limit for AI mode
            if action == "ai":
                u = user(user_id)
                if not is_admin and u["ai_used"] >= u["daily_limit"]:
                    await query.edit_message_text("سهمیه امروز شما برای استیکر پیشرفته تمام شده است.", reply_markup=back_to_menu_kb())
                    return

            user_packs = get_user_packs(user_id)
            if not user_packs:
                s["pack_wizard"] = {"step": "awaiting_name"}
                await query.edit_message_text(
                    "ابتدا باید یک پک استیکر بسازید. یک نام انگلیسی برای پک خود بنویسید (مثال: my_stickers).",
                    reply_markup=back_to_menu_kb()
                )
            else:
                await query.edit_message_text("می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟", reply_markup=pack_selection_kb(user_id))

    elif mode == "pack":
        action = parts[1]
        if action == "new":
            sess(user_id)["pack_wizard"] = {"step": "awaiting_name"}
            await query.edit_message_text(
                "یک نام انگلیسی برای پک جدید خود بنویسید (مثال: my_stickers).",
                reply_markup=back_to_menu_kb()
            )
        elif action == "select":
            pack_short_name = parts[2]

            # Find the pack to ensure it exists
            user_packs = get_user_packages(user_id)
            selected_pack = next((p for p in user_packs if p["short_name"] == pack_short_name), None)

            if selected_pack:
                users = _load_data(USERS_FILE)
                users[str(user_id)]["current_pack"] = pack_short_name
                _save_data(USERS_FILE, users)

                s = sess(user_id)
                if s["mode"] == "simple":
                    await query.edit_message_text(f"پک «{selected_pack['name']}» انتخاب شد.\n\nحالا متن استیکر خود را بفرستید.")
                elif s["mode"] == "ai":
                    await query.edit_message_text(f"پک «{selected_pack['name']}» انتخاب شد.\n\nحالا متن استیکر پیشرفته خود را بفرستید.")
            else:
                await query.edit_message_text("خطایی در انتخاب پک رخ داد. لطفا دوباره تلاش کنید.", reply_markup=back_to_menu_kb())

    elif query.data == "check_membership":
        is_member = await check_channel_membership(context.bot, user_id)
        if is_member:
            await query.edit_message_text(
                "عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.",
                reply_markup=main_menu_kb(is_admin)
            )
        else:
            await query.answer("شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)

    elif mode == "sticker":
        action = parts[1]
        if action == "confirm":
            s = sess(user_id)
            sticker_data = s.get("data", {})
            current_pack = get_current_pack(user_id)

            if not sticker_data.get("text") or not current_pack:
                await query.edit_message_text("خطایی رخ داد. لطفا دوباره تلاش کنید.", reply_markup=back_to_menu_kb())
                return

            try:
                # Re-render the sticker with final parameters
                final_sticker_bytes = render_image(
                    text=sticker_data["text"], v_pos="center", h_pos="center",
                    color_hex="#FFFFFF", size_key="medium"
                )

                success = await context.bot.add_sticker_to_set(
                    user_id=user_id,
                    name=current_pack["short_name"],
                    sticker=InputSticker(final_sticker_bytes, ["😊"])
                )

                if success:
                    await query.edit_message_text(
                        f"استیکر با موفقیت به پک «{current_pack['name']}» اضافه شد!\n\n"
                        f"لینک پک: https://t.me/addstickers/{current_pack['short_name']}",
                        reply_markup=main_menu_kb(is_admin)
                    )
                    reset_mode(user_id)
                else:
                    await query.edit_message_text("خطایی در افزودن استیکر به پک رخ داد.", reply_markup=back_to_menu_kb())

            except Exception as e:
                logger.error(f"Error adding sticker to set: {e}")
                await query.edit_message_text(f"خطا: {e}", reply_markup=back_to_menu_kb())

        elif action == "edit":
            await query.edit_message_text("بخش ویرایش در حال ساخت است.", reply_markup=back_to_menu_kb())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all text messages."""
    user_id = update.effective_user.id
    s = sess(user_id)
    text = update.message.text

    if s.get("pack_wizard", {}).get("step") == "awaiting_name":
        pack_name = text.strip().lower()

        # Forbidden words check
        if any(word in pack_name for word in FORBIDDEN_WORDS):
            await update.message.reply_text("نام پک حاوی کلمات غیرمجاز است. لطفاً نام دیگری انتخاب کنید.", reply_markup=back_to_menu_kb())
            return

        # Basic validation
        if not pack_name.isalpha() or len(pack_name) > 20:
             await update.message.reply_text("نام پک نامعتبر است. لطفاً یک نام انگلیسی کوتاه‌تر و بدون فاصله انتخاب کنید.", reply_markup=back_to_menu_kb())
             return

        bot_username = (await context.bot.get_me()).username
        pack_short_name = f"{pack_name}_by_{bot_username}"

        try:
            # Create a placeholder sticker
            dummy_sticker_bytes = render_image("اولین استیکر!", "center", "center", "#FFFFFF", "medium")

            success = await context.bot.create_new_sticker_set(
                user_id=user_id,
                name=pack_short_name,
                title=f"{pack_name} by @{bot_username}",
                stickers=[InputSticker(dummy_sticker_bytes, ["🎉"])],
                sticker_format="static"
            )

            if success:
                add_user_pack(user_id, pack_name, pack_short_name)
                s["pack_wizard"] = {}
                update_sess(user_id, s)

                await update.message.reply_text(
                    f"پک «{pack_name}» با موفقیت ساخته شد!\n\nحالا متن استیکر خود را بفرستید.",
                    reply_markup=back_to_menu_kb()
                )
            else:
                await update.message.reply_text("خطایی در ساخت پک استیکر رخ داد. لطفاً دوباره تلاش کنید.", reply_markup=back_to_menu_kb())

        except Exception as e:
            logger.error(f"Error creating sticker set {pack_short_name}: {e}")
            await update.message.reply_text(f"خطا: {e}. ممکن است این نام پک قبلاً توسط شما یا دیگران استفاده شده باشد.", reply_markup=back_to_menu_kb())
        return

    elif s.get("mode") in ["simple", "ai"]:
        s["data"]["text"] = text

        # Default preview
        img_bytes = render_image(
            text=text, v_pos="center", h_pos="center",
            color_hex="#FFFFFF", size_key="medium"
        )

        keyboard = [
            [InlineKeyboardButton("تایید و افزودن به پک", callback_data="sticker:confirm")],
            [InlineKeyboardButton("ویرایش", callback_data="sticker:edit")],
            [InlineKeyboardButton("انصراف", callback_data="menu:home")]
        ]

        await update.message.reply_photo(
            photo=img_bytes,
            caption="پیش‌نمایش استیکر شما. می‌توانید آن را تایید کنید یا به ویرایش ادامه دهید.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def my_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's sticker packs"""
    user_id = update.effective_user.id
    packages = get_user_packages(user_id)
    
    if not packages:
        await update.message.reply_text("🎨 شما هنوز پک استیکری نساخته‌اید!\n\nبرای ساخت اولین استیکر، روی دکمه 🎨 ساخت استیکر سریع کلیک کنید.")
        return
    
    text = "📦 **پک‌های استیکر شما:**\n\n"
    keyboard = []
    
    for pkg in packages:
        text += f"🎨 {pkg['name']}\n"
        text += f"📊 تعداد استیکر: {len(pkg.get('stickers', []))}\n"
        text += f"📅 ساخته شده: {pkg.get('created_at', 'N/A')}\n\n"
        
        if 'url' in pkg:
            keyboard.append([InlineKeyboardButton(
                f"🔗 {pkg['name']}", 
                url=pkg['url']
            )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Flask Routes

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Telegram webhook handler"""
    if telegram_app:
        update = Update.de_json(request.get_json(), telegram_app.bot)
        asyncio.run(telegram_app.process_update(update))
    return "OK", 200

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

def setup_telegram_app():
    """Setup telegram application"""
    global telegram_app
    if BOT_TOKEN:
        telegram_app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("my_packs", my_packs))
        telegram_app.add_handler(CallbackQueryHandler(button_handler))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        
        return telegram_app
    return None

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is required!")
        exit(1)
    
    # Setup Telegram app
    bot_app = setup_telegram_app()
    
    # Set webhook if running in production
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url and bot_app:
        logger.info(f"Setting webhook to: {webhook_url}")
        asyncio.run(bot_app.bot.set_webhook(webhook_url))
    
    # Run Flask app
    app.run(host='0.0.0.0', port=PORT)