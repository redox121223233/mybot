#!/usr/bin/env python3
"""
Simple Telegram Sticker Bot - Optimized for Vercel
Fixed CancelledError and simplified webhook handling
"""

import os
import json
import logging
import asyncio
import tempfile
import io
from datetime import datetime, timezone, timedelta
import uuid
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
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

# Bot Configuration
ADMIN_ID = 6053579919
SUPPORT_USERNAME = "@onedaytoalive"
ADVANCED_DAILY_LIMIT = 3
WEB_APP_URL = "https://see-my-branches.lovable.app"  # آدرس وب اپلیکیشن شما

# Data Storage
USERS = {}
USER_LIMITS = {}

def load_data():
    """Load data from files"""
    global USERS, USER_LIMITS
    try:
        if os.path.exists("/tmp/users.json"):
            with open("/tmp/users.json", 'r') as f:
                USERS = json.load(f)
        if os.path.exists("/tmp/limits.json"):
            with open("/tmp/limits.json", 'r') as f:
                USER_LIMITS = json.load(f)
    except:
        pass

def save_data():
    """Save data to files"""
    try:
        with open("/tmp/users.json", 'w') as f:
            json.dump(USERS, f)
        with open("/tmp/limits.json", 'w') as f:
            json.dump(USER_LIMITS, f)
    except:
        pass

def get_limits(user_id: int) -> dict:
    """Get user limits"""
    if user_id not in USER_LIMITS:
        USER_LIMITS[user_id] = {
            "advanced_used": 0,
            "last_reset": datetime.now(timezone.utc).isoformat()
        }
        save_data()
    return USER_LIMITS[user_id]

def reset_daily_limit(user_id: int):
    """Reset daily limit if 24 hours passed"""
    limits = get_limits(user_id)
    try:
        last_reset = datetime.fromisoformat(limits["last_reset"])
        if (datetime.now(timezone.utc) - last_reset) >= timedelta(hours=24):
            limits["advanced_used"] = 0
            limits["last_reset"] = datetime.now(timezone.utc).isoformat()
            save_data()
    except:
        limits["advanced_used"] = 0
        limits["last_reset"] = datetime.now(timezone.utc).isoformat()
        save_data()

def can_use_advanced(user_id: int) -> bool:
    """Check if user can use advanced mode"""
    reset_daily_limit(user_id)
    return get_limits(user_id)["advanced_used"] < ADVANCED_DAILY_LIMIT

def use_advanced(user_id: int):
    """Use one advanced sticker"""
    limits = get_limits(user_id)
    limits["advanced_used"] += 1
    save_data()

def get_remaining(user_id: int) -> int:
    """Get remaining advanced stickers"""
    reset_daily_limit(user_id)
    return ADVANCED_DAILY_LIMIT - get_limits(user_id)["advanced_used"]

def create_sticker(text: str, image_data: bytes) -> bytes:
    """Create simple sticker"""
    try:
        # Load image
        img = Image.open(io.BytesIO(image_data))
        img = img.convert('RGBA')
        
        # Resize to fit 512x512
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        
        # Create canvas
        canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        # Center the image
        x_offset = (512 - img.width) // 2
        y_offset = (512 - img.height) // 2
        canvas.paste(img, (x_offset, y_offset), img)
        
        draw = ImageDraw.Draw(canvas)
        
        # Process Arabic text
        if re.search(r'[\u0600-\u06FF]', text):
            try:
                text = arabic_reshaper.reshape(text)
                text = get_display(text)
            except:
                pass
        
        # Load font
        font = None
        for font_path in ["fonts/Vazirmatn-Regular.ttf", "fonts/IRANSans.ttf"]:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, 40)
                    break
                except:
                    continue
        
        if not font:
            font = ImageFont.load_default()
        
        # Get text dimensions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Center text
        x = (512 - text_width) // 2
        y = (512 - text_height) // 2
        
        # Add shadow
        draw.text((x+2, y+2), text, font=font, fill="#000000")
        
        # Draw main text
        draw.text((x, y), text, font=font, fill="#FFFFFF")
        
        # Save as WebP
        output = io.BytesIO()
        canvas.save(output, format='WebP', quality=95)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        return None

# Session storage
SESSIONS = {}

def get_session(user_id: int) -> dict:
    """Get user session"""
    if user_id not in SESSIONS:
        SESSIONS[user_id] = {}
    return SESSIONS[user_id]

def clear_session(user_id: int):
    """Clear user session"""
    if user_id in SESSIONS:
        del SESSIONS[user_id]

# Main menu with WebApp button
def get_main_menu():
    """Get main menu keyboard"""
    return [
        [InlineKeyboardButton("🚀 باز کردن برنامه ساخت استیکر", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
    ]

# Initialize bot
def init_bot():
    """Initialize bot application"""
    # Load data
    load_data()
    
    # Setup bot
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found")
        return None
    
    application = Application.builder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    return application

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start"""
    user_id = update.effective_user.id
    
    # Register user
    if user_id not in USERS:
        USERS[user_id] = {
            "first_name": update.effective_user.first_name,
            "joined_at": datetime.now(timezone.utc).isoformat()
        }
        save_data()
    
    text = """🎨 **به ربات استیکر ساز خوش آمدید!** 🌟

    برای ساخت استیکرهای زیبا و سفارشی، از برنامه وب ما استفاده کنید.

    👇 **روی دکمه زیر کلیک کنید تا شروع کنید!**
    """
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu()))

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ فقط ادمین!")
        return
    
    text = f"""👨‍💼 پنل ادمین

👥 کاربران: {len(USERS)}
⚡ محدودیت روزانه: {ADVANCED_DAILY_LIMIT}
🎯 وضعیت: فعال ✅"""
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu()))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    text = f"""📖 راهنمای ربات استیکر ساز

🌐 **Mini App:**
• 🚀 باز کردن وب اپلیکیشن حرفه‌ای
• 📱 رابط کاربری مدرن و فارسی
• ⚡ سرعت بالا و بدون نیاز به دانلود

🎨 **استیکر ساز:**
• ✅ ساده: فقط عکس + متن
• ⚡ پیشرفته: ۳ بار در روز با تنظیمات

📊 **سهمیه:**
• مشاهده تعداد استیکرهای باقی‌مانده
• زمان باقی‌مانده تا ریست شدن

📞 **پشتیبانی:**
• ادمین: {SUPPORT_USERNAME}

📝 **نحوه استفاده:**
۱. 🚀 روی دکمه "باز کردن Mini App" کلیک کنید
۲. 📱 از وب اپلیکیشن برای ساخت استیکر استفاده کنید
۳. 💾 استیکر ساخته شده را دانلود کنید"""
    
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu()))
    else:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu()))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "help":
        # Let the help_cmd function handle the response
        await help_cmd(update, context)

    elif data == "support":
        text = f"""📞 **پشتیبانی ربات**

        👨‍💼 ادمین: {SUPPORT_USERNAME}

        برای سوالات و مشکلات با ادمین در تماس باشید.
        """
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back":
        # This will bring the user back to the main menu
        # It's good practice to re-send the start message
        # in case the original one was deleted or is far up in the chat.
        user_id = update.effective_user.id
        if user_id not in USERS:
            USERS[user_id] = {
                "first_name": update.effective_user.first_name,
                "joined_at": datetime.now(timezone.utc).isoformat()
            }
            save_data()
        
        start_text = """🎨 **به ربات استیکر ساز خوش آمدید!** 🌟

        برای ساخت استیکر، از دکمه زیر استفاده کنید:
        """
        await query.edit_message_text(start_text, reply_markup=InlineKeyboardMarkup(get_main_menu()))

# Global application
application = None

# Vercel Handler Class
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    """Vercel Python handler class"""
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {"status": "ok", "message": "Sticker Bot is running!", "web_app": WEB_APP_URL}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"GET handler error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests (Telegram webhook)"""
        global application
        if application is None:
            application = init_bot()

        try:
            # Initialize bot if not already done
            if application is None:
                raise Exception("Failed to initialize bot")

            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            if post_data:
                # Parse JSON data
                data = json.loads(post_data.decode('utf-8'))
                
                # Process update
                update = Update.de_json(data, application.bot)
                
                # Process the update
                asyncio.run(application.process_update(update))
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {"status": "ok"}
                self.wfile.write(json.dumps(response).encode())
            else:
                # No data received
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                response = {"status": "error", "message": "No data received"}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            logger.error(f"POST handler error: {e}")
            self.send_response(200)  # Always return 200 to Telegram
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response).encode())

# Lazy initialization on first POST request