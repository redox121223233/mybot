#!/usr/bin/env python3
"""
Perfect Button System - Simple, Fast, Reliable
Sticker Creator Bot with Button Interface
"""

import os
import json
import logging
import asyncio
import tempfile
import io
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, InputSticker
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Vercel
app = Flask(__name__)

# Bot Configuration
BOT_USERNAME = "@matnsticker_bot"
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = 6053579919
SUPPORT_USERNAME = "@onedaytoalive"

# Initialize Application
application = None

async def get_application():
    global application
    if application is None:
        application = Application.builder().token(BOT_TOKEN).build()
    return application

def create_default_sticker_image():
    """Create a simple default sticker"""
    # Create a 512x512 image with gradient background
    img = Image.new('RGBA', (512, 512), (102, 126, 234, 255))
    draw = ImageDraw.Draw(img)
    
    # Add gradient effect
    for i in range(512):
        color = (
            102 + int(i * 0.1),
            126 + int(i * 0.1),
            234 - int(i * 0.1),
            255
        )
        draw.line([(0, i), (512, i)], fill=color)
    
    # Add emoji text
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
    except:
        font = ImageFont.load_default()
    
    text = "🎨"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (512 - text_width) // 2
    y = (512 - text_height) // 2
    
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    
    return img

def create_text_sticker_image(text="عالی!", font_size=48, color="#ffffff"):
    """Create a text-based sticker"""
    img = Image.new('RGBA', (512, 512), (118, 75, 162, 255))
    draw = ImageDraw.Draw(img)
    
    # Process Arabic text
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
    except:
        bidi_text = text
    
    # Load font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Calculate text position
    bbox = draw.textbbox((0, 0), bidi_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (512 - text_width) // 2
    y = (512 - text_height) // 2
    
    # Add shadow
    shadow_offset = 4
    draw.text((x + shadow_offset, y + shadow_offset), bidi_text, font=font, fill=(0, 0, 0, 200))
    
    # Draw main text
    draw.text((x, y), bidi_text, font=font, fill=color)
    
    return img

def image_to_webp_bytes(img):
    """Convert PIL Image to WebP bytes"""
    webp_buffer = io.BytesIO()
    img.save(webp_buffer, format='WebP', quality=90)
    webp_buffer.seek(0)
    return webp_buffer.getvalue()

def image_to_data_url(img):
    """Convert PIL Image to Data URL"""
    webp_bytes = image_to_webp_bytes(img)
    base64_str = base64.b64encode(webp_bytes).decode('utf-8')
    return f"data:image/webp;base64,{base64_str}"

# Flask Routes
@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Telegram Bot Webhook"""
    try:
        update_data = request.get_json()
        if not update_data:
            return jsonify({"status": "no data"}), 200
        
        update = Update.de_json(update_data, bot)
        
        async def _process_update():
            app = await get_application()
            await app.process_update(update)
        
        asyncio.run(_process_update())
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/create-default-sticker', methods=['POST'])
def create_default_sticker():
    """Create a default sticker"""
    async def _create_sticker():
        try:
            app = await get_application()
            bot = app.bot
            
            data = request.get_json()
            user_id = data.get('user_id')
            
            if not user_id:
                return jsonify({"error": "User ID required"}), 400
            
            logger.info(f"Creating default sticker for user {user_id}")
            
            # Create sticker image
            sticker_img = create_default_sticker_image()
            sticker_bytes = image_to_webp_bytes(sticker_img)
            
            # Create sticker pack name
            pack_name = f"default_pack_{user_id % 10000}_by_{bot.username}"
            pack_title = f"استیکر‌های پیش‌فرض کاربر {user_id % 10000}"
            
            # Create InputSticker
            sticker_input = InputSticker(
                sticker=io.BytesIO(sticker_bytes),
                format="static",
                emoji_list=["🎨"]
            )
            
            try:
                # Try to add to existing pack
                await bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_name,
                    sticker=sticker_input
                )
            except:
                # Create new pack
                await bot.create_new_sticker_set(
                    user_id=user_id,
                    name=pack_name,
                    title=pack_title,
                    stickers=[sticker_input]
                )
            
            pack_url = f"https://t.me/addstickers/{pack_name}"
            
            # Send success message to user
            await bot.send_message(
                user_id,
                f"✅ استیکر پیش‌فرض با موفقیت ساخته شد!\n\n🔗 لینک پک استیکر:\n{pack_url}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 باز کردن پک استیکر", url=pack_url)]
                ])
            )
            
            logger.info(f"Default sticker created successfully for user {user_id}")
            
            return jsonify({
                "success": True,
                "message": "Default sticker created successfully",
                "pack_url": pack_url
            }), 200
            
        except Exception as e:
            logger.error(f"Error creating default sticker: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            if application:
                await application.shutdown()
    
    return asyncio.run(_create_sticker())

@app.route('/api/create-text-sticker', methods=['POST'])
def create_text_sticker():
    """Create a text-based sticker"""
    async def _create_sticker():
        try:
            app = await get_application()
            bot = app.bot
            
            data = request.get_json()
            user_id = data.get('user_id')
            text = data.get('text', 'عالی!')
            font_size = data.get('font_size', 48)
            color = data.get('color', '#ffffff')
            
            if not user_id:
                return jsonify({"error": "User ID required"}), 400
            
            logger.info(f"Creating text sticker for user {user_id}: {text}")
            
            # Create sticker image
            sticker_img = create_text_sticker_image(text, font_size, color)
            sticker_bytes = image_to_webp_bytes(sticker_img)
            
            # Create sticker pack name
            pack_name = f"text_pack_{user_id % 10000}_by_{bot.username}"
            pack_title = f"استیکر‌های متنی کاربر {user_id % 10000}"
            
            # Create InputSticker
            sticker_input = InputSticker(
                sticker=io.BytesIO(sticker_bytes),
                format="static",
                emoji_list=["✨"]
            )
            
            try:
                # Try to add to existing pack
                await bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_name,
                    sticker=sticker_input
                )
            except:
                # Create new pack
                await bot.create_new_sticker_set(
                    user_id=user_id,
                    name=pack_name,
                    title=pack_title,
                    stickers=[sticker_input]
                )
            
            pack_url = f"https://t.me/addstickers/{pack_name}"
            
            # Send success message to user
            await bot.send_message(
                user_id,
                f"✅ استیکر متنی «{text}» با موفقیت ساخته شد!\n\n🔗 لینک پک استیکر:\n{pack_url}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📦 باز کردن پک استیکر", url=pack_url)]
                ])
            )
            
            logger.info(f"Text sticker created successfully for user {user_id}")
            
            return jsonify({
                "success": True,
                "message": "Text sticker created successfully",
                "pack_url": pack_url
            }), 200
            
        except Exception as e:
            logger.error(f"Error creating text sticker: {e}")
            return jsonify({"error": str(e)}), 500
        finally:
            if application:
                await application.shutdown()
    
    return asyncio.run(_create_sticker())

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test API health"""
    try:
        test_data = {
            "status": "working",
            "message": "Perfect Button System API is working",
            "timestamp": datetime.now().isoformat(),
            "bot_username": BOT_USERNAME,
            "version": "2.0.0"
        }
        
        logger.info("🧪 Perfect Button System - Test endpoint working")
        return jsonify(test_data), 200
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return jsonify({"error": str(e)}), 500

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

    **🚀 روش استفاده:**
    1. روی دکمه «ساخت استیکر سریع» کلیک کنید
    2. نوع استیکر مورد نظر را انتخاب کنید
    3. صبر کنید تا استیکر ساخته شود
    4. لینک پک استیکر در تلگرام برای شما ارسال می‌شود

    **⚡ انواع استیکر:**
    • استیکر سریع - طراحی پیش‌فرض زیبا
    • استیکر متنی - متن دلخواه روی پس‌زمینه
    • ویرایش عکس - تبدیل عکس به استیکر

    **📞 پشتیبانی:**
    @onedaytoalive
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Main Flask app
if __name__ == "__main__":
    # Get bot instance for webhook
    bot = Bot(token=BOT_TOKEN)
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=8080)