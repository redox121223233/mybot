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
MINI_APP_URL = os.getenv('MINI_APP_URL', 'https://your-domain.railway.app')
ADMIN_ID = 6053579919
ADVANCED_DAILY_LIMIT = 3

# Data storage (in production, use a database)
USER_PACKAGES: dict[int, list] = {}
USER_LIMITS: dict[int, dict] = {}

# Global application
telegram_app = None

def get_user_packages(user_id: int) -> list:
    """Get user's sticker packages"""
    if user_id not in USER_PACKAGES:
        USER_PACKAGES[user_id] = []
    return USER_PACKAGES[user_id]

def get_user_limits(user_id: int) -> dict:
    """Get user limits"""
    if user_id not in USER_LIMITS:
        USER_LIMITS[user_id] = {
            "advanced_used": 0,
            "last_reset": datetime.now(timezone.utc).isoformat()
        }
    return USER_LIMITS[user_id]

def reset_daily_limit(user_id: int):
    """Reset daily advanced limit if needed"""
    limits = get_user_limits(user_id)
    last_reset = datetime.fromisoformat(limits["last_reset"])
    if datetime.now(timezone.utc) - last_reset > timedelta(days=1):
        limits["advanced_used"] = 0
        limits["last_reset"] = datetime.now(timezone.utc).isoformat()

def create_text_sticker_image(text: str, text_color: str = '#FFFFFF', background_color: str = '#000000') -> Image.Image:
    """Create a text sticker image with transparency support"""
    img = Image.new('RGBA', (512, 512), (0, 0, 0, 0) if background_color == 'transparent' else background_color)
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("Vazirmatn-Regular.ttf", 48)
    except:
        font = ImageFont.load_default()
    
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
    except:
        bidi_text = text
    
    if font:
        bbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = len(bidi_text) * 10
        text_height = 48
    
    x = (512 - text_width) // 2
    y = (512 - text_height) // 2
    
    draw.text((x, y), bidi_text, fill=text_color, font=font)
    return img

def create_advanced_text_sticker(text: str, text_color: str = '#FFFFFF', background_color: str = 'transparent', font_size: int = 48) -> Image.Image:
    """Create an advanced text sticker with better transparency and rendering"""
    img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    
    if background_color != 'transparent':
        if background_color.startswith('#'):
            bg_color = tuple(int(background_color[i:i+2], 16) for i in (1, 3, 5))
            bg_img = Image.new('RGB', (512, 512), bg_color)
            img = Image.new('RGBA', (512, 512))
            img.paste(bg_img)
    
    draw = ImageDraw.Draw(img)
    
    try:
        font_paths = ["Vazirmatn-Regular.ttf", "Vazirmatn-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
        if not font:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
    except:
        bidi_text = text
    
    if font and hasattr(font, 'getbbox'):
        bbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = len(bidi_text) * (font_size // 2)
        text_height = font_size
    
    x = (512 - text_width) // 2
    y = (512 - text_height) // 2
    
    shadow_offset = 2
    shadow_color = (0, 0, 0, 128) if background_color == 'transparent' else (0, 0, 0)
    draw.text((x + shadow_offset, y + shadow_offset), bidi_text, fill=shadow_color, font=font)
    
    if text_color.startswith('#'):
        text_color_rgb = tuple(int(text_color[i:i+2], 16) for i in (1, 3, 5))
        draw.text((x, y), bidi_text, fill=text_color_rgb, font=font)
    else:
        draw.text((x, y), bidi_text, fill=text_color, font=font)
    
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.2)
    
    return img

def image_to_webp_bytes(img: Image.Image) -> bytes:
    """Convert PIL Image to WebP bytes"""
    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=95, method=6)
    return buffer.getvalue()

# Bot Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    keyboard = [
        [InlineKeyboardButton("🎨 ساخت استیکر سریع", web_app=WebAppInfo(url=MINI_APP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎨 به ربات استیکر ساز خوش آمدید!\n\n"
        "🌟 **امکانات ویژه:**\n"
        "⚡ ساخت استیکر سریع و آسان\n"
        "✏️ طراحی استیکر متنی با فونت فارسی\n"
        "🎨 انتخاب رنگ و پس‌زمینه دلخواه\n"
        "📦 مدیریت پک استیکر شخصی\n\n"
        "👇 برای شروع روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🎨 **ربات استیکر ساز حرفه‌ای**

**🚀 امکانات:**
• 🎯 ساخت استیکر متن فارسی با فونت‌های متنوع
• 🌈 انتخاب رنگ و پس‌زمینه دلخواه  
• 📸 تبدیل عکس به استیکر
• 📦 مدیریت پک استیکر شخصی
• ⚡ عملکرد سریع و رابط کاربری آسان

**📱 دستورات:**
/start - شروع و ساخت استیکر
/help - مشاهده این راهنما
/my_packs - پک‌های استیکر شما

🔗 [وب‌اپ ربات](URL)

❓ نیاز به راهنمایی؟ پشتیبانی در دسترس است!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

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
    
    keyboard.append([InlineKeyboardButton(
        "🎨 ساخت استیکر جدید", 
        web_app=WebAppInfo(url=MINI_APP_URL)
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Flask Routes
@app.route('/')
def home():
    """Home route with mini app"""
    return '''
    <!DOCTYPE html>
    <html lang="fa" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ربات استیکر ساز</title>
        <style>
            body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }
            .container { background: white; border-radius: 20px; padding: 40px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; max-width: 400px; }
            .emoji { font-size: 60px; margin-bottom: 20px; }
            h1 { color: #333; margin-bottom: 20px; }
            p { color: #666; margin-bottom: 30px; line-height: 1.6; }
            .btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 15px 30px; border-radius: 25px; font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; transition: transform 0.2s; }
            .btn:hover { transform: scale(1.05); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">🎨</div>
            <h1>ربات استیکر ساز</h1>
            <p>با این ربات حرفه‌ای، به سادگی استیکرهای دلخواه خود را بسازید!</p>
            <a href="https://t.me/your_bot_username" class="btn">🚀 شروع کنید</a>
        </div>
    </body>
    </html>
    '''

@app.route('/api/create-default-sticker', methods=['POST'])
def create_default_sticker():
    """Create a default sticker"""
    try:
        data = request.get_json()
        text = data.get('text', 'استیکر پیش‌فرض')
        color = data.get('color', '#FFFFFF')
        background_color = data.get('background_color', '#000000')
        
        sticker_image = create_text_sticker_image(text, color, background_color)
        
        buffer = io.BytesIO()
        sticker_image.save(buffer, format='WEBP', quality=95, method=6)
        sticker_base64 = base64.b64encode(buffer.getvalue()).decode()
        sticker_data = f"data:image/webp;base64,{sticker_base64}"
        
        return jsonify({
            'success': True,
            'sticker': sticker_data,
            'message': 'Default sticker created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating default sticker: {e}")
        return jsonify({'error': 'Failed to create default sticker'}), 500

@app.route('/api/create-text-sticker', methods=['POST'])
def create_text_sticker():
    """Create a custom text sticker"""
    try:
        data = request.get_json()
        text = data.get('text', 'استیکر متنی')
        color = data.get('color', '#FFFFFF')
        background_color = data.get('background_color', 'transparent')
        font_size = data.get('font_size', 48)
        
        if not text:
            return jsonify({'error': 'Text required'}), 400
            
        sticker_image = create_advanced_text_sticker(text, color, background_color, font_size)
        
        buffer = io.BytesIO()
        if background_color == 'transparent':
            sticker_image.save(buffer, format='WEBP', quality=95, method=6, lossless=False)
        else:
            sticker_image.save(buffer, format='WEBP', quality=95, method=6)
        sticker_base64 = base64.b64encode(buffer.getvalue()).decode()
        sticker_data = f"data:image/webp;base64,{sticker_base64}"
        
        return jsonify({
            'success': True,
            'sticker': sticker_data,
            'message': 'Text sticker created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating text sticker: {e}")
        return jsonify({'error': 'Failed to create text sticker'}), 500

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