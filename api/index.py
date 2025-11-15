#!/usr/bin/env python3
"""
Enhanced Telegram Sticker Bot - Vercel Fixed Version with Mini App Integration and Proper Initialization
"""

import os
import json
import logging
import asyncio
import io
import re
from typing import Dict, Any, Optional

# Import Flask
from flask import Flask, request, send_from_directory

from telegram import Update, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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
app = Flask(__name__, static_folder='../', static_url_path='')

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

        font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'Vazirmatn-Regular.ttf')
        font = ImageFont.truetype(font_path, 60)

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
    keyboard = [[
        {"text": "ورود به مینی اپ", "web_app": {"url": "https://mybot32.vercel.app"}}
    ]]
    reply_markup = {"inline_keyboard": keyboard}

    await update.message.reply_text(
        "برای کار با ربات به مینی اپ بروید.",
        reply_markup=reply_markup
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "راهنمای ربات:\n"
        "/start - شروع ربات\n"
        "/help - نمایش راهنما\n"
        "برای ساخت استیکر، از مینی اپ استفاده کنید."
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("این دستور فقط برای مدیر است!")
        return
    await update.message.reply_text("پنل مدیریت:\nربات فعال و آماده به کار است.")

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("admin", admin))
application.add_handler(CommandHandler("help", help_cmd))

# Flask Routes
@app.route('/')
def index():
    return send_from_directory('../', 'index.html')

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Webhook handler that properly initializes and shuts down the application."""
    async def handle_update():
        await application.initialize()
        try:
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
        finally:
            await application.shutdown()

    try:
        load_data()
        asyncio.run(handle_update())
        save_data()
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

@app.route('/api/create-sticker', methods=['POST'])
def create_sticker_api():
    """API for website sticker creation"""
    try:
        data = request.get_json()
        text = data.get('text', '')

        image_data = None
        if 'image' in data and data['image']:
            import base64
            image_b64 = data['image'].split(',')[1]
            image_data = base64.b64decode(image_b64)

        sticker_bytes = create_sticker(text, image_data)

        if sticker_bytes:
            import base64
            sticker_base64 = base64.b64encode(sticker_bytes).decode('utf-8')
            return {"sticker": f"data:image/webp;base64,{sticker_base64}"}, 200
        else:
            return {"error": "Failed to create sticker"}, 500

    except Exception as e:
        logger.error(f"API error: {e}")
        return {"error": "Server error"}, 500

@app.route('/api/add-sticker-to-pack', methods=['POST'])
def add_sticker_to_pack_api():
    """API for adding a sticker to a pack from the Mini App."""
    async def _add_sticker():
        await application.initialize()
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            pack_name = data.get('pack_name')
            sticker_b64 = data.get('sticker').split(',')[1]
            sticker_bytes = base64.b64decode(sticker_b64)

            if not all([user_id, pack_name, sticker_bytes]):
                return {"error": "Missing required data"}, 400

            bot = application.bot
            # Pack names must end with '_by_<bot_username>'
            full_pack_name = f"{pack_name}_by_{bot.username}"

            try:
                # This will throw an error if the pack doesn't exist
                await bot.get_sticker_set(full_pack_name)
                # Pack exists, add the new sticker
                await bot.add_sticker_to_set(user_id=user_id, name=full_pack_name, sticker=sticker_bytes, emojis=['😊'])
                pack_url = f"https://t.me/addstickers/{full_pack_name}"
                await bot.send_message(user_id, f"✅ استیکر با موفقیت به پک شما اضافه شد:\n{pack_url}")
            except Exception:
                # Pack does not exist, so create it
                await bot.create_new_sticker_set(user_id=user_id, name=full_pack_name, title=pack_name, sticker=sticker_bytes, emojis=['😊'])
                pack_url = f"https://t.me/addstickers/{full_pack_name}"
                await bot.send_message(user_id, f"🎉 پک استیکر شما با موفقیت ساخته شد:\n{pack_url}")

            return {"success": True, "message": "Sticker added successfully"}, 200
        except Exception as e:
            logger.error(f"Add sticker API error: {e}")
            return {"error": "Server error"}, 500
        finally:
            await application.shutdown()

    return asyncio.run(_add_sticker())

@app.route('/api/log', methods=['POST'])
def log_event():
    """Endpoint to log frontend events."""
    try:
        data = request.get_json()
        level = data.get('level', 'INFO').upper()
        message = data.get('message', '')

        if message:
            # Log using the standard logger, Vercel will capture this
            logger.log(logging.getLevelName(level), f"Frontend Log: {message}")

        return {"status": "logged"}, 200
    except Exception as e:
        # Don't log errors here to avoid loops
        return {"status": "error"}, 500
