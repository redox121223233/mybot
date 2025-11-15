#!/usr/bin/env python3
"""
Enhanced Telegram Sticker Bot - Vercel Fixed Version with Restored Functionality
"""

import os
import json
import logging
import asyncio
import io
import re
from typing import Dict, Any, Optional

# Import Flask
from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Vercel
app = Flask(__name__)

# Bot Configuration
ADMIN_ID = 6053579919

# Data Storage paths in /tmp for Vercel
USERS_FILE = '/tmp/users.json'
LIMITS_FILE = '/tmp/limits.json'
PACKS_FILE = '/tmp/packs.json'

# Data Storage
USERS: Dict[int, Dict[str, Any]] = {}
USER_LIMITS: Dict[int, Dict[str, Any]] = {}
STICKER_PACKS: Dict[str, Dict[str, Any]] = {}
SESSIONS: Dict[int, Dict[str, Any]] = {}

def load_data():
    """Load data from files in /tmp"""
    global USERS, USER_LIMITS, STICKER_PACKS
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                USERS = json.load(f)
        if os.path.exists(LIMITS_FILE):
            with open(LIMITS_FILE, 'r') as f:
                USER_LIMITS = json.load(f)
        if os.path.exists(PACKS_FILE):
            with open(PACKS_FILE, 'r') as f:
                STICKER_PACKS = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_data():
    """Save data to files in /tmp"""
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(USERS, f)
        with open(LIMITS_FILE, 'w') as f:
            json.dump(USER_LIMITS, f)
        with open(PACKS_FILE, 'w') as f:
            json.dump(STICKER_PACKS, f)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def get_session(user_id: int) -> Dict[str, Any]:
    """Get user session"""
    if user_id not in SESSIONS:
        SESSIONS[user_id] = {}
    return SESSIONS[user_id]

def clear_session(user_id: int):
    """Clear user session"""
    if user_id in SESSIONS:
        del SESSIONS[user_id]

def create_sticker(text: str, image_data: Optional[bytes] = None) -> bytes:
    """Create a sticker with text and optional image."""
    try:
        canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))

        if image_data:
            img = Image.open(io.BytesIO(image_data))
            img = img.convert('RGBA')
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            x_offset = (512 - img.width) // 2
            y_offset = (512 - img.height) // 2
            canvas.paste(img, (x_offset, y_offset), img)
        
        draw = ImageDraw.Draw(canvas)
        
        if re.search(r'[\u0600-\u06FF]', text):
            text = arabic_reshaper.reshape(text)
            text = get_display(text)
        
        font = ImageFont.truetype("fonts/Vazirmatn-Regular.ttf", 60)
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (512 - text_width) / 2
        y = (512 - text_height) / 2

        draw.text((x + 2, y + 2), text, font=font, fill="#000000")
        draw.text((x, y), text, font=font, fill="#FFFFFF")

        output = io.BytesIO()
        canvas.save(output, format='WebP')
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error in create_sticker: {e}")
        return None

# Initialize bot application
bot_token = os.environ.get("BOT_TOKEN")
if not bot_token:
    logger.error("BOT_TOKEN not found in environment variables")
application = Application.builder().token(bot_token).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"سلام {user.first_name}! به ربات استیکر ساز خوش آمدید.\n"
        "یک عکس برایم بفرستید تا آن را به استیکر تبدیل کنم."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "راهنمای ربات:\n"
        "/start - شروع ربات\n"
        "/help - نمایش راهنما\n"
        "برای ساخت استیکر، یک عکس بفرستید و سپس متن مورد نظرتان را ارسال کنید."
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("این دستور فقط برای مدیر است!")
        return
    await update.message.reply_text("پنل مدیریت:\nربات فعال و آماده به کار است.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_session(user_id)

    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        session["image"] = photo_bytes
        session["waiting_text"] = True

        await update.message.reply_text("✅ عکس دریافت شد! حالا متن خود را بنویسید.")
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ خطا در دریافت عکس.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session.get("waiting_text"):
        await update.message.reply_text("لطفا ابتدا یک عکس بفرستید.")
        return

    text = update.message.text
    image_data = session.get("image")

    if not image_data:
        await update.message.reply_text("خطا: عکسی یافت نشد. لطفا دوباره عکس را ارسال کنید.")
        clear_session(user_id)
        return

    await update.message.reply_text("⏳ در حال ساخت استیکر...")

    try:
        sticker_bytes = create_sticker(text, image_data)

        if sticker_bytes:
            sticker_file = io.BytesIO(sticker_bytes)
            await update.message.reply_sticker(sticker=sticker_file)
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر.")
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        await update.message.reply_text("❌ یک خطای غیرمنتظره رخ داد.")
    finally:
        clear_session(user_id)

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("admin", admin))
application.add_handler(CommandHandler("help", help_cmd))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

@app.route('/')
def home():
    return "Sticker Bot is running!"

@app.route('/api/webhook', methods=['POST'])
def webhook():
    try:
        load_data()

        if request.is_json:
            update_data = request.get_json()
            update = Update.de_json(update_data, application.bot)
            asyncio.run(application.process_update(update))
            save_data()
            return "OK"
        else:
            return "Invalid request", 400
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500
