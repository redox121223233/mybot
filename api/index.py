#!/usr/bin/env python3
"""
Web App برای Vercel - مدیریت ربات تلگرامی با طراحی شیشه‌ای
Vercel Compatible Web App for Telegram Bot
"""

import os
import json
import logging
import asyncio
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import subprocess

from flask import Flask, request, jsonify
from telegram import Update, BotCommand
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

# Flask App for Vercel
app = Flask(__name__)

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    logger.warning("BOT_TOKEN not properly configured!")

CHANNEL_USERNAME = "@redoxbot_sticker"
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919

MAINTENANCE = False
DAILY_LIMIT = 5

# Data Storage (in-memory for Vercel)
USERS: Dict[int, Dict[str, Any]] = {}
SESSIONS: Dict[int, Dict[str, Any]] = {}

# Global application
telegram_app = None

def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return int(midnight.timestamp())

def _reset_daily_if_needed(u: Dict[str, Any]):
    day_start = u.get("day_start")
    today = _today_start_ts()
    if day_start is None or day_start < today:
        u["day_start"] = today
        u["ai_used"] = 0

def user(uid: int) -> Dict[str, Any]:
    if uid not in USERS:
        USERS[uid] = {
            "ai_used": 0, 
            "vote": None, 
            "day_start": _today_start_ts(), 
            "packs": [],
            "current_pack": None
        }
    _reset_daily_if_needed(USERS[uid])
    return USERS[uid]

def sess(uid: int) -> Dict[str, Any]:
    if uid not in SESSIONS:
        SESSIONS[uid] = {
            "mode": "menu",
            "ai": {},
            "simple": {},
            "pack_wizard": {},
            "await_feedback": False,
            "last_sticker": None,
        }
    return SESSIONS[uid]

def _load_local_fonts() -> Dict[str, str]:
    return {
        "vazir": "Vazirmatn-Regular.ttf",
        "sans": "DejaVuSans.ttf",
        "roboto": "Roboto-Regular.ttf"
    }

def resolve_font_path(font_key: Optional[str], text: str = "") -> str:
    fonts = _load_local_fonts()
    
    if font_key and font_key in fonts:
        return fonts[font_key]
    
    # Check for Persian text
    if re.search(r'[\u0600-\u06FF]', text):
        return fonts["vazir"]
    return fonts["sans"]

def _prepare_text(text: str) -> str:
    text = text.strip()
    if len(text) > 150:
        words = text.split()
        text = ' '.join(words[:30])
        if len(text) < len(text.strip()):
            text += "..."
    return text

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = hx.lstrip('#')
    if len(hx) == 3:
        hx = ''.join(c*2 for c in hx)
    try:
        rgb = tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))
        return (*rgb, 255)
    except:
        return (0, 0, 0, 255)

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    for size in range(base, 20, -1):
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_w and h <= max_h:
            return size
    return 25

def _make_default_bg(size=(512, 512)) -> Image.Image:
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Glassmorphism pattern
    for i in range(0, size[0], 40):
        for j in range(0, size[1], 40):
            if (i // 40 + j // 40) % 2 == 0:
                draw.rectangle([(i, j), (i+39, j+39)], fill=(255, 255, 255, 20))
    
    return img

def render_image(text: str, font_key: str, color_hex: str, size_key: str, bg_mode: str = "default") -> Image.Image:
    W, H = 512, 512
    text = _prepare_text(text)
    
    # Handle Persian text
    if re.search(r'[\u0600-\u06FF]', text):
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            reshaped_text = arabic_reshaper.reshape(text)
            text = get_display(reshaped_text)
        except:
            pass
    
    img = _make_default_bg((W, H)) if bg_mode == "default" else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font_path = resolve_font_path(font_key, text)
        base_size = 70 if size_key == "large" else 55 if size_key == "medium" else 40
        final_size = fit_font_size(draw, text, font_path, base_size, W-60, H-60)
        font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    x = (W - text_w) // 2
    y = (H - text_h) // 2
    
    color = _parse_hex(color_hex)
    draw.text((x, y), text, fill=color, font=font)
    return img

# Import needed for regex
import re

# Telegram Bot Handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    SESSIONS[uid] = {"mode": "menu"}
    
    welcome_text = f"""
✨ **به ربات استیکر ساز خوش آمدید!** ✨

🎯 یک ربات حرفه‌ای با طراحی شیشه‌ای مدرن

🔥 **ویژگی‌های اصلی:**
• 🎨 ساخت استیکر متن (فارسی و انگلیسی)
• 🌦 پس‌زمینه شیشه‌ای زیبا
• 📊 سیستم سهمیه روزانه
• 🌟 کیفیت عالی و سرعت بالا

📝 **لطفاً متن خود را بنویسید:**
    """
    
    await update.message.reply_text(welcome_text, reply_markup=main_menu_kb())

def main_menu_kb():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.utils.keyboard import InlineKeyboardBuilder
    
    builder = InlineKeyboardBuilder()
    
    # Glassmorphism style menu
    builder.row(
        InlineKeyboardButton(text="🎨 ساخت استیکر", callback_data="create_sticker"),
        InlineKeyboardButton(text="✨ استیکر پیشرفته", callback_data="advanced_sticker")
    )
    
    builder.row(
        InlineKeyboardButton(text="📊 آمار من", callback_data="my_stats"),
        InlineKeyboardButton(text="❓ راهنما", callback_data="help")
    )
    
    builder.row(
        InlineKeyboardButton(text="🌐 کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"),
        InlineKeyboardButton(text="💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")
    )
    
    return builder.as_markup()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    
    if text:
        await update.message.reply_text("🎨 در حال ساخت استیکر شما...")
        
        try:
            img = render_image(
                text=text,
                font_key="vazir",
                color_hex="#FFFFFF",
                size_key="large",
                bg_mode="default"
            )
            
            bio = BytesIO()
            bio.name = 'sticker.png'
            img.save(bio, 'PNG')
            bio.seek(0)
            
            await update.message.reply_sticker(bio)
            await update.message.reply_text("✅ استیکر شما با موفقیت ساخته شد!")
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "create_sticker":
        await query.message.edit_text("🎨 لطفاً متن استیکر خود را بنویسید:")
    elif query.data == "advanced_sticker":
        await query.message.edit_text("✨ ویژگی پیشرفته - به زودی!")
    elif query.data == "my_stats":
        uid = update.effective_user.id
        u = user(uid)
        await query.message.edit_text(f"📊 آمار شما:\nاستیکرهای ساخته شده: {u.get('ai_used', 0)}")
    elif query.data == "help":
        help_text = """
📖 **راهنمای ربات:**

1. متن خود را بفرستید
2. استیکر خود را دریافت کنید
3. از پس‌زمینه شیشه‌ای لذت ببرید

🎨 پشتیبانی از فارسی و انگلیسی
        """
        await query.message.edit_text(help_text)

# Initialize Telegram Application
async def init_telegram_app():
    global telegram_app
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN not configured!")
        return None
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Set bot commands
    await application.bot.set_my_commands([
        BotCommand("start", "شروع ربات"),
        BotCommand("help", "راهنما"),
    ])
    
    logger.info("Telegram bot initialized successfully")
    return application

# Vercel Handler
@app.route("/", methods=["GET", "POST"])
async def webhook():
    global telegram_app
    
    if request.method == "GET":
        return jsonify({"status": "ok", "message": "Sticker Bot is running on Vercel!"})
    
    if request.method == "POST":
        try:
            if not telegram_app:
                telegram_app = await init_telegram_app()
                if not telegram_app:
                    return jsonify({"error": "Bot not initialized"}), 500
            
            update_data = request.get_json()
            if not update_data:
                return jsonify({"error": "No update data"}), 400
            
            # Create Update object
            update = Update.de_json(update_data, telegram_app.bot)
            
            # Process update
            await telegram_app.process_update(update)
            
            return jsonify({"status": "ok"})
            
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return jsonify({"error": str(e)}), 500

# Health check endpoint
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

# Vercel needs a handler variable
handler = app

# For local testing
if __name__ == "__main__":
    app.run(debug=True, port=5000)