#!/usr/bin/env python3
"""
Hybrid Solution: Vercel Static + Bot Commands
Keep Vercel for static hosting, add bot buttons for functionality
"""
import os
import logging
import asyncio
import io
import base64
from datetime import datetime, timezone, timedelta

from flask import Flask, request, send_from_directory, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import arabic_reshaper
from bidi.algorithm import get_display

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 6053579919

# In-memory storage (use database in production)
USER_DATA = {}

def create_quick_sticker(text="استیکر سریع", color="#FFFFFF"):
    """Create quick sticker"""
    img = Image.new('RGBA', (512, 512), (118, 75, 162, 255))
    draw = ImageDraw.Draw(img)
    
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
    except:
        bidi_text = text
    
    try:
        font = ImageFont.truetype("Vazirmatn-Regular.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    if font:
        bbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = len(bidi_text) * 15
        text_height = 60
    
    x = (512 - text_width) // 2
    y = (512 - text_height) // 2
    
    draw.text((x, y), bidi_text, fill=color, font=font)
    return img

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start with bot buttons"""
    user_id = update.effective_user.id
    
    keyboard = [
        [
            InlineKeyboardButton("⚡ استیکر سریع", callback_data="quick_sticker"),
            InlineKeyboardButton("✏️ استیکر متنی", callback_data="text_sticker")
        ],
        [
            InlineKeyboardButton("🎨 ویژگی‌های پیشرفته", url="https://mybot32.vercel.app"),
            InlineKeyboardButton("📚 راهنما", callback_data="help")
        ],
        [
            InlineKeyboardButton("📦 پک‌های من", callback_data="my_packs")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = """
🎨 **به ربات استیکر ساز خوش آمدید!**

🚀 **دو راه برای ساخت استیکر دارید:**

**۱. سریع و آسان (دکمه‌های زیر):**
⚡ استیکرهای آماده و سریع
✏️ استیکر متنی دلخواه

**۲. پیشرفته و حرفه‌ای:**
🎨 وب‌اپ با امکانات کامل

👇 یکی را انتخاب کنید:
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """
🎯 **راهنمای کامل ربات استیکر ساز**

**⚡ ساخت سریع:**
- استیکر سریع: طراحی فوری
- استیکر متنی: متن دلخواه شما

**🎨 وب‌اپ پیشرفته:**
- طراحی کامل و حرفه‌ای
- پیش‌نمایش زنده
- امکانات نامحدود

**📱 دستورات:**
/start - شروع و منوی اصلی
/help - این راهنما
/my_packs - پک‌های شما

❓ هر سوالی دارید بپرسید!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "quick_sticker":
        # Create quick sticker
        texts = ["عالیه!", "سپاسگزارم", "عالی بود", "دمت گرم", "خفن❤️"]
        import random
        text = random.choice(texts)
        
        sticker_img = create_quick_sticker(text)
        buffer = io.BytesIO()
        sticker_img.save(buffer, format='WEBP')
        sticker_bytes = buffer.getvalue()
        
        # Send sticker directly
        await context.bot.send_sticker(
            chat_id=user_id,
            sticker=sticker_bytes
        )
        
        await query.edit_message_text(
            f"✅ استیکر سریع ساخته شد!\n\n"
            f"متن: {text}\n\n"
            f"برای ساخت استیکر دیگر دوباره /start را بزنید."
        )
    
    elif data == "text_sticker":
        # Ask for text
        await query.edit_message_text(
            "✏️ **لطفاً متن مورد نظر خود را ارسال کنید:**\n\n"
            "متن شما به استیکر تبدیل خواهد شد!\n\n"
            "مثال: سلام دنیا 🌍",
            parse_mode='Markdown'
        )
        # Store state for next message
        USER_DATA[user_id] = {"waiting_for_text": True}
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "my_packs":
        await query.edit_message_text(
            "📦 **پک‌های استیکر شما:**\n\n"
            "در حال حاضر پکی ندارید.\n\n"
            "با ساخت اولین استیکر، پک شما ساخته می‌شود! 🎨",
            parse_mode='Markdown'
        )

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for custom sticker creation"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check if user is waiting to provide text for sticker
    if user_id in USER_DATA and USER_DATA[user_id].get("waiting_for_text"):
        # Create custom text sticker
        sticker_img = create_quick_sticker(text, "#FFFFFF")
        buffer = io.BytesIO()
        sticker_img.save(buffer, format='WEBP')
        sticker_bytes = buffer.getvalue()
        
        await context.bot.send_sticker(
            chat_id=user_id,
            sticker=sticker_bytes
        )
        
        await update.message.reply_text(
            f"✅ استیکر متنی شما ساخته شد!\n\n"
            f"متن: {text}\n\n"
            f"برای ساخت استیکر دیگر /start را بزنید. 🎨"
        )
        
        # Clear state
        del USER_DATA[user_id]

# Flask routes for Vercel
@app.route('/')
def home():
    """Serve mini app"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Webhook handler"""
    if BOT_TOKEN:
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
        
        try:
            update = Update.de_json(request.get_json(), application.bot)
            asyncio.run(application.process_update(update))
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    return "OK", 200

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is required!")
        exit(1)
    
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))