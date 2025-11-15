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
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Flask
app = Flask(__name__, static_folder='../public', static_url_path='')

# Configuration
ADMIN_ID = 6053579919
ADVANCED_DAILY_LIMIT = 3
MINI_APP_URL = "https://mybot32.vercel.app/miniapp"  # Current deployment URL

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
    """Reset daily limit if 24 hours passed"""
    limits = get_user_limits(user_id)
    try:
        last_reset = datetime.fromisoformat(limits["last_reset"])
        if (datetime.now(timezone.utc) - last_reset) >= timedelta(hours=24):
            limits["advanced_used"] = 0
            limits["last_reset"] = datetime.now(timezone.utc).isoformat()
    except:
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

def get_remaining(user_id: int) -> int:
    """Get remaining advanced stickers"""
    reset_daily_limit(user_id)
    return ADVANCED_DAILY_LIMIT - get_user_limits(user_id)["advanced_used"]

def create_sticker(text: str, image_data: Optional[bytes] = None, 
                   position_x: int = 256, position_y: int = 256,
                   font_size: int = 40, text_color: str = "#FFFFFF",
                   font_family: str = "Vazirmatn") -> bytes:
    """Create sticker with all advanced controls"""
    try:
        canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        if image_data:
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            canvas.paste(img, (int((512 - img.width) / 2), int((512 - img.height) / 2)), img)
        else:
            # Create gradient background if no image
            for y in range(512):
                r = int(255 - (y * 50 / 512))
                g = int(107 - (y * 30 / 512))
                b = int(107 - (y * 30 / 512))
                for x in range(512):
                    canvas.putpixel((x, y), (r, g, b))
        
        draw = ImageDraw.Draw(canvas)
        if re.search(r'[\u0600-\u06FF]', text):
            text = arabic_reshaper.reshape(text)
            text = get_display(text)

        # Load font with fallback
        font_path = os.path.join(os.path.dirname(__file__), f'../public/fonts/{font_family}-Regular.ttf')
        if not os.path.exists(font_path):
            font_path = os.path.join(os.path.dirname(__file__), '../public/fonts/Vazirmatn-Regular.ttf')
        if not os.path.exists(font_path):
            font = ImageFont.load_default()
        else:
            font = ImageFont.truetype(font_path, font_size)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = position_x - text_width // 2
        y = position_y - text_height // 2
        
        # Shadow
        draw.text((x + 2, y + 2), text, font=font, fill="#000000")
        # Main text
        draw.text((x, y), text, font=font, fill=text_color)

        output = io.BytesIO()
        canvas.save(output, format='WebP', quality=80, optimize=True)
        output.seek(0)
        
        # Check file size and compress further if needed
        file_size = len(output.getvalue())
        if file_size > 64 * 1024:  # If larger than 64KB
            logger.warning(f"Sticker size {file_size} bytes, compressing further...")
            canvas.save(output, format='WebP', quality=60, optimize=True, method=6)
            output.seek(0)
            file_size = len(output.getvalue())
            logger.info(f"Compressed to {file_size} bytes")
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error in create_sticker: {e}")
        return None

# Initialize Telegram Bot
bot_token = os.environ.get("BOT_TOKEN")
if not bot_token:
    logger.error("BOT_TOKEN not found in environment variables")
application = Application.builder().token(bot_token).build()

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with mini app integration"""
    keyboard = [[InlineKeyboardButton("🎨 استیکر ساز (مینی اپ)", web_app=WebAppInfo(url=MINI_APP_URL))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = (
        "🎨 **به ربات استیکر ساز خوش آمدید!**\n\n"
        "✨ **ویژگی‌های مینی اپ جدید:**\n"
        "📦 ساخت پک استیکر با نام دلخواه (اجباری)\n"
        "🎨 دو نوع استیکر: ساده و پیشرفته\n"
        "⚙️ تنظیمات کامل متن (اندازه، رنگ، موقعیت، فونت)\n"
        "👀 پیش نمایش زنده استیکر\n"
        "🔗 دریافت لینک پک برای نصب و اشتراک‌گذاری\n\n"
        "روی دکمه زیر کلیک کنید تا مینی اپ باز شود:"
    )
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    text = (
        "📖 **راهنمای ربات**\n\n"
        "🎨 **مینی اپ استیکر ساز:**\n"
        "• ساخت پک استیکر با نام دلخواه (اجباری)\n"
        "• استیکر ساده: نامحدود استفاده (عکس + متن)\n"
        "• استیکر پیشرفته: 3 بار در روز (عکس + متن + تنظیمات کامل)\n\n"
        "📊 **سهمیه من:**\n"
        "• نمایش تعداد استیکر پیشرفته باقی‌مانده\n"
        "• نمایش زمان تا ریست شدن سهمیه\n\n"
        "📝 **نحوه استفاده:**\n"
        "۱. روی 🎨 استیکر ساز (مینی اپ) کلیک کنید\n"
        "۲. نام پک را وارد کنید (اجباری)\n"
        "۳. عکس و متن خود را آپلود کنید\n"
        "۴. تنظیمات را سفارشی کرده و استیکر بسازید\n"
        "۵. لینک پک را برای نصب دریافت کنید"
    )
    
    keyboard = [[InlineKeyboardButton("🎨 باز کردن مینی اپ", web_app=WebAppInfo(url=MINI_APP_URL))]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def quota_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user quota"""
    user_id = update.effective_user.id
    reset_daily_limit(user_id)
    remaining = get_remaining(user_id)
    used = ADVANCED_DAILY_LIMIT - remaining
    
    text = (
        f"📊 **سهمیه شما**\n\n"
        f"🎨 **استیکر ساده:**\n"
        f"✅ نامحدود\n\n"
        f"⚡ **استیکر پیشرفته:**\n"
        f"📈 استفاده شده: {used} از {ADVANCED_DAILY_LIMIT}\n"
        f"📊 باقی‌مانده: {remaining} استیکر"
    )
    
    keyboard = [[InlineKeyboardButton("🎨 باز کردن مینی اپ", web_app=WebAppInfo(url=MINI_APP_URL))]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Register bot handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_cmd))
application.add_handler(CommandHandler("quota", quota_cmd))

# Flask routes
@app.route('/')
def index():
    """Serve main mini app page"""
    return send_from_directory('../templates', 'miniapp.html')

@app.route('/miniapp')
def miniapp():
    """Serve mini app page"""
    return send_from_directory('../templates', 'miniapp.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory(app.static_folder, path)

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Telegram webhook handler"""
    async def handle_update():
        await application.initialize()
        try:
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
        finally:
            await application.shutdown()
    asyncio.run(handle_update())
    return "OK", 200

@app.route('/api/add-sticker-to-pack', methods=['POST'])
def add_sticker_to_pack_api():
    """Enhanced sticker pack API with all features"""
    async def _add_sticker():
        await application.initialize()
        try:
            data = request.get_json()
            user_id = data.get('user_id')
            pack_name = data.get('pack_name')
            sticker_b64 = data.get('sticker', '')
            
            # Validate required fields
            if not all([user_id, pack_name, sticker_b64]):
                return jsonify({"error": "Missing required data: user_id, pack_name, and sticker are required"}), 400
            
            # Extract image data
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

            # Check advanced limits
            if sticker_type == 'advanced':
                if not can_use_advanced(user_id):
                    return jsonify({"error": "Daily advanced limit exceeded"}), 429
                use_advanced(user_id)

            # Create sticker with advanced options
            sticker_bytes = create_sticker(
                text=text,
                image_data=sticker_bytes,
                position_x=position_x,
                position_y=position_y,
                font_size=font_size,
                text_color=text_color,
                font_family=font_family
            )

            if not sticker_bytes:
                return jsonify({"error": "Failed to create sticker"}), 500

            bot = application.bot
            full_pack_name = f"{pack_name.lower().replace(' ', '_')}_by_{bot.username}"

            try:
                # Try to add to existing pack
                await bot.get_sticker_set(full_pack_name)
                await bot.add_sticker_to_set(user_id=user_id, name=full_pack_name, stickers=[sticker_bytes], emojis=["😀"])
                pack_url = f"https://t.me/addstickers/{full_pack_name}"
                
                # Store in user packages
                packages = get_user_packages(user_id)
                for pkg in packages:
                    if pkg['name'] == pack_name:
                        pkg['stickers'].append({'text': text, 'type': sticker_type})
                        break
                else:
                    packages.append({
                        'name': pack_name,
                        'url': pack_url,
                        'stickers': [{'text': text, 'type': sticker_type}],
                        'created_at': datetime.now(timezone.utc).isoformat()
                    })
                
                await bot.send_message(
                    user_id, 
                    f"✅ استیکر با موفقیت به پک «{pack_name}» اضافه شد:\n{pack_url}"
                )
                
            except Exception as e:
                # Create new pack
                await bot.create_new_sticker_set(
                    user_id=user_id, 
                    name=full_pack_name, 
                    title=pack_name, 
                    stickers=[sticker_bytes], 
                    emojis=['😊']
                )
                pack_url = f"https://t.me/addstickers/{full_pack_name}"
                
                # Store new pack
                packages = get_user_packages(user_id)
                packages.append({
                    'name': pack_name,
                    'url': pack_url,
                    'stickers': [{'text': text, 'type': sticker_type}],
                    'created_at': datetime.now(timezone.utc).isoformat()
                })
                
                await bot.send_message(
                    user_id, 
                    f"🎉 پک استیکر «{pack_name}» با موفقیت ساخته شد:\n{pack_url}"
                )

            return jsonify({
                "success": True, 
                "message": "Sticker added successfully",
                "pack_url": pack_url,
                "remaining_advanced": get_remaining(user_id)
            }), 200
            
        except Exception as e:
            logger.error(f"Add sticker API error: {e}")
            return jsonify({"error": "Server error"}), 500
        finally:
            await application.shutdown()
    return asyncio.run(_add_sticker())

@app.route('/api/user-info', methods=['POST'])
def get_user_info():
    """Get user information and packages"""
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        packages = get_user_packages(user_id)
        remaining = get_remaining(user_id)
        
        return jsonify({
            'packages': packages,
            'remaining_advanced': remaining,
            'advanced_limit': ADVANCED_DAILY_LIMIT
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
