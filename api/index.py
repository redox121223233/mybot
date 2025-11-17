#!/usr/bin/env python3
"""
Enhanced Telegram Sticker Bot - Mini App Integration Version
Fixed all mini app issues with package creation and advanced features
"""
import os
import json
import logging
import asyncio
import io
import re
import base64
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from flask import Flask, request, send_from_directory, jsonify
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import arabic_reshaper
from bidi.algorithm import get_display

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Flask
app = Flask(__name__, static_folder='../public', static_url_path='')

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
PORT = int(os.getenv('PORT', 5000))
MINI_APP_URL = "https://mybot32.vercel.app"
ADMIN_ID = 6053579919
ADVANCED_DAILY_LIMIT = 3
SUPPORT_USERNAME = "@onedaytoalive"

# Initialize Application
application = None

# Data storage
USER_PACKAGES: dict[int, list] = {}
USER_LIMITS: dict[int, dict] = {}

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

def can_use_advanced(user_id: int) -> bool:
    """Check if user can use advanced mode"""
    reset_daily_limit(user_id)
    return get_user_limits(user_id)["advanced_used"] < ADVANCED_DAILY_LIMIT

def use_advanced(user_id: int):
    """Use one advanced sticker"""
    limits = get_user_limits(user_id)
    limits["advanced_used"] += 1

def create_text_sticker_image(text: str, text_color: str = '#FFFFFF', background_color: str = '#000000') -> Image.Image:
    """Create a text sticker image with transparency support"""
    # Create transparent or colored background
    img = Image.new('RGBA', (512, 512), (0, 0, 0, 0) if background_color == 'transparent' else background_color)
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to load Persian font
        font = ImageFont.truetype("Vazirmatn-Regular.ttf", 48)
    except:
        try:
            # Fallback to default font
            font = ImageFont.load_default()
        except:
            font = None
    
    # Process Arabic/Persian text
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    # Calculate text position for center alignment
    if font:
        bbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = len(bidi_text) * 10
        text_height = 48
    
    x = (512 - text_width) // 2
    y = (512 - text_height) // 2
    
    # Draw text with anti-aliasing
    draw.text((x, y), bidi_text, fill=text_color, font=font)
    
    return img

def create_advanced_text_sticker(text: str, text_color: str = '#FFFFFF', background_color: str = 'transparent', font_size: int = 48) -> Image.Image:
    """Create an advanced text sticker with better transparency and rendering"""
    # Create high-quality transparent background
    img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    
    # Add background if not transparent
    if background_color != 'transparent':
        if background_color.startswith('#'):
            # Convert hex to RGB
            bg_color = tuple(int(background_color[i:i+2], 16) for i in (1, 3, 5))
            bg_img = Image.new('RGB', (512, 512), bg_color)
            img = Image.new('RGBA', (512, 512))
            img.paste(bg_img)
        else:
            img = Image.new('RGBA', (512, 512), background_color)
    
    draw = ImageDraw.Draw(img)
    
    try:
        # Try multiple font options
        font_paths = [
            "Vazirmatn-Regular.ttf",
            "Vazirmatn-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Arial.ttf"
        ]
        
        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
        
        if not font:
            font = ImageFont.load_default()
            
    except Exception as e:
        logger.warning(f"Font loading failed: {e}")
        font = ImageFont.load_default()
    
    # Process Arabic/Persian text with proper shaping
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
    except:
        bidi_text = text
    
    # Calculate text position with better centering
    if font and hasattr(font, 'getbbox'):
        bbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        text_width = len(bidi_text) * (font_size // 2)
        text_height = font_size
    
    x = (512 - text_width) // 2
    y = (512 - text_height) // 2
    
    # Add shadow for better readability
    shadow_offset = 2
    shadow_color = (0, 0, 0, 128) if background_color == 'transparent' else (0, 0, 0)
    draw.text((x + shadow_offset, y + shadow_offset), bidi_text, fill=shadow_color, font=font)
    
    # Draw main text
    if text_color.startswith('#'):
        text_color_rgb = tuple(int(text_color[i:i+2], 16) for i in (1, 3, 5))
        draw.text((x, y), bidi_text, fill=text_color_rgb, font=font)
    else:
        draw.text((x, y), bidi_text, fill=text_color, font=font)
    
    # Enhance image quality
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.2)
    
    return img

def create_default_sticker_image() -> Image.Image:
    """Create a default sticker with gradient background"""
    # Create gradient background
    img = Image.new('RGBA', (512, 512), (118, 75, 162, 255))
    draw = ImageDraw.Draw(img)
    
    # Add text
    text = "عالی!"
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
    
    draw.text((x, y), bidi_text, font=font, fill=(255, 255, 255, 255))
    
    return img

def image_to_webp_bytes(img: Image.Image) -> bytes:
    """Convert PIL Image to WebP bytes"""
    buffer = io.BytesIO()
    img.save(buffer, format='WEBP', quality=95, method=6)
    return buffer.getvalue()

async def get_application():
    global application
    if application is None:
        application = Application.builder().token(BOT_TOKEN).build()
    return application

# Flask Routes
@app.route('/')
def home():
    """Serve the main web app"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/miniapp')
def miniapp():
    """Serve the mini app"""
    return send_from_directory('../templates', 'miniapp.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Telegram webhook handler"""
    async def handle_update():
        app_bot = await get_application()
        try:
            await app_bot.initialize()
            update = Update.de_json(request.get_json(force=True), app_bot.bot)
            await app_bot.process_update(update)
        finally:
            try:
                await app_bot.shutdown()
            except:
                pass
    asyncio.run(handle_update())
    return "OK", 200

@app.route('/api/create-default-sticker', methods=['POST'])
def create_default_sticker():
    """Create a default sticker with transparency fix"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        text = data.get('text', 'استیکر پیش‌فرض')
        color = data.get('color', '#FFFFFF')
        background_color = data.get('background_color', '#000000')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
            
        # Create sticker with transparency fix
        sticker_image = create_text_sticker_image(text, color, background_color)
        
        # Convert to base64 with proper transparency handling
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
    """Create a custom text sticker with transparency support"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        text = data.get('text', 'استیکر متنی')
        color = data.get('color', '#FFFFFF')
        background_color = data.get('background_color', 'transparent')
        font_size = data.get('font_size', 48)
        
        if not user_id or not text:
            return jsonify({'error': 'User ID and text required'}), 400
            
        # Create sticker with advanced text rendering
        sticker_image = create_advanced_text_sticker(text, color, background_color, font_size)
        
        # Convert to base64 with transparency preservation
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

@app.route('/api/add-sticker-to-pack', methods=['POST'])
def add_sticker_to_pack_api():
    """Enhanced sticker pack API with all features"""
    async def _add_sticker():
        app_bot = await get_application()
        bot = app_bot.bot
        
        data = request.get_json()
        user_id = data.get('user_id')
        pack_name = data.get('pack_name')
        sticker_b64 = data.get('sticker', '')
        
        # Validate required fields (sticker is now optional)
        if not all([user_id, pack_name]):
            return jsonify({"error": "Missing required data: user_id and pack_name are required"}), 400
        
        # Extract image data (can be None for gradient background)
        sticker_bytes = None
        if sticker_b64:
            if ',' in sticker_b64:
                sticker_b64 = sticker_b64.split(',')[1]
            sticker_bytes = base64.b64decode(sticker_b64)

        # Get advanced options
        text = data.get('text', 'استیکر')
        sticker_type = data.get('type', 'simple')
        font_size = int(data.get('font_size', 40))
        font_family = data.get('font_family', 'Vazirmatn')
        text_color = data.get('text_color', '#FFFFFF')
        position_x = int(data.get('position_x', 256))
        position_y = int(data.get('position_y', 256))

        # Check advanced limits (text-only mode doesn't count)
        if sticker_type == 'advanced':
            if not can_use_advanced(user_id):
                return jsonify({"error": "Daily advanced limit exceeded"}), 429
            use_advanced(user_id)

        # For text-only mode, use no image
        if sticker_type == 'text-only':
            sticker_bytes = None

        # Create image if needed
        if not sticker_bytes:
            img = create_text_sticker_image(
                text, 
                text_color, 
                data.get('background_color', 'transparent')
            )
            sticker_bytes = image_to_webp_bytes(img)

        # Create pack name with bot username
        full_pack_name = f"{pack_name}_by_{bot.username}"
        
        try:
            # Try to add to existing pack
            await bot.get_sticker_set(full_pack_name)
            # Create InputSticker object for the new API format
            input_sticker = InputSticker(
                sticker=sticker_bytes,
                emoji_list=['😊']
            )
            
            await bot.add_sticker_to_set(user_id=user_id, name=full_pack_name, sticker=input_sticker)
            pack_url = f"https://t.me/addstickers/{full_pack_name}"
            
            # Store in user packages
            packages = get_user_packages(user_id)
            for pkg in packages:
                if pkg['name'] == pack_name:
                    pkg['stickers'].append({'text': text, 'type': sticker_type})
                    break
            
            return jsonify({
                "success": True,
                "pack_url": pack_url,
                "message": "Sticker added to existing pack"
            })
            
        except TelegramError as e:
            if "STICKERSET_INVALID" in str(e):
                # Create new pack
                input_sticker = InputSticker(
                    sticker=sticker_bytes,
                    emoji_list=['😊']
                )
                
                await bot.create_new_sticker_set(
                    user_id=user_id, 
                    name=full_pack_name, 
                    title=pack_name, 
                    stickers=[input_sticker]
                )
                
                pack_url = f"https://t.me/addstickers/{full_pack_name}"
                
                # Store new pack
                packages = get_user_packages(user_id)
                packages.append({
                    'name': pack_name,
                    'full_name': full_pack_name,
                    'url': pack_url,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'stickers': [{'text': text, 'type': sticker_type}]
                })
                
                return jsonify({
                    "success": True,
                    "pack_url": pack_url,
                    "message": "New sticker pack created"
                })
            else:
                raise e
                
    try:
        return asyncio.run(_add_sticker())
    except Exception as e:
        logger.error(f"Error in add_sticker_to_pack: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/user-info', methods=['POST'])
def get_user_info():
    """Get user package info and limits"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        packages = get_user_packages(user_id)
        limits = get_user_limits(user_id)
        reset_daily_limit(user_id)
        
        return jsonify({
            'packages': packages,
            'limits': {
                'advanced_used': limits['advanced_used'],
                'advanced_limit': ADVANCED_DAILY_LIMIT,
                'advanced_remaining': max(0, ADVANCED_DAILY_LIMIT - limits['advanced_used'])
            }
        })
        
    except Exception as e:
        logger.error(f"Error in user info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/log', methods=['POST'])
def log_event():
    """Frontend logging"""
    data = request.get_json()
    logger.info(f"Frontend Log: [{data.get('level', 'INFO').upper()}] {data.get('message', '')}")
    return jsonify({"status": "logged"}), 200

# Bot Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    keyboard = [
        [InlineKeyboardButton("🎨 ساخت استیکر سریع", web_app=WebAppInfo(url="https://mybot32.vercel.app"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎨 به ربات استیکر ساز خوش آمدید!\n\n"
        "با یک کلیک استیکر خود را بسازید:\n"
        "⚡ ساخت استیکر سریع\n"
        "✏️ ساخت استیکر متنی\n"
        "📸 ویرایش عکس استیکر\n\n"
        "روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🎨 **راهنمای ربات استیکر ساز**

**امکانات:**
• 🎯 ساخت استیکر متن فارسی
• 🌈 انتخاب رنگ و فونت
• 📸 ویرایش عکس به استیکر
• 📦 مدیریت پک استیکر
• ⚡ عملکرد سریع و آسان

**دستورات:**
/start - شروع ربات
/help - مشاهده راهنما
/my_packs - پک‌های شما

🔗 [وب‌اپ ربات](https://mybot32.vercel.app)

❓ سوال؟ @onedaytoalive
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def my_packs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's sticker packs"""
    user_id = update.effective_user.id
    packages = get_user_packages(user_id)
    
    if not packages:
        await update.message.reply_text("شما هنوز پک استیکری نساخته‌اید!")
        return
    
    text = "📦 **پک‌های استیکر شما:**\n\n"
    keyboard = []
    
    for pkg in packages:
        text += f"🎨 {pkg['name']}\n"
        text += f"📊 تعداد استیکر: {len(pkg.get('stickers', []))}\n"
        text += f"📅 ساخته شده: {pkg.get('created_at', 'N/A')}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"🔗 {pkg['name']}", 
            url=pkg['url']
        )])
    
    keyboard.append([InlineKeyboardButton(
        "🎨 ساخت استیکر جدید", 
        web_app=WebAppInfo(url="https://mybot32.vercel.app")
    )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Main setup
def setup_bot():
    """Setup bot handlers"""
    app_bot = Application.builder().token(BOT_TOKEN).build()
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("help", help_command))
    app_bot.add_handler(CommandHandler("my_packs", my_packs))
    
    return app_bot

if __name__ == "__main__":
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is required!")
        exit(1)
    
    # Setup bot
    bot_app = setup_bot()
    
    # Start bot polling
    bot_app.run_polling(drop_pending_updates=True)
    
    # Start Flask app (for webhook mode)
    app.run(host='0.0.0.0', port=PORT)