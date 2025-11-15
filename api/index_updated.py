#!/usr/bin/env python3
"""
Updated Telegram Bot with Mini App Integration
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
from flask import Flask, request

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
SUPPORT_USERNAME = "@onedaytoalive"
ADVANCED_DAILY_LIMIT = 3
MINI_APP_URL = "https://your-vercel-domain.vercel.app/miniapp/"  # Update this with your Vercel URL

# Data Storage
USERS: dict[int, dict] = {}
USER_LIMITS: dict[int, dict] = {}

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

def create_sticker(text: str, image_data: bytes, 
                   position_x: int = 256, position_y: int = 256,
                   font_size: int = 40, color: str = "#FFFFFF") -> bytes:
    """Create sticker"""
    try:
        # Load image
        img = Image.open(io.BytesIO(image_data))
        img = img.convert('RGBA')
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        
        # Create canvas
        canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
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
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        if not font:
            font = ImageFont.load_default()
        
        # Draw text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = position_x - text_width // 2
        y = position_y - text_height // 2
        
        # Shadow
        draw.text((x+2, y+2), text, font=font, fill="#000000")
        # Main text
        draw.text((x, y), text, font=font, fill=color)
        
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

# Main menu
def get_main_menu():
    """Get main menu keyboard"""
    return [
        [InlineKeyboardButton("🎨 استیکر ساز (مینی اپ)", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("📊 سهمیه من", callback_data="quota")],
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
    ]

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
    
    text = (
        "🎨 به ربات استیکر ساز خوش آمدید!\n\n"
        "✨ **ویژگی‌های جدید مینی اپ:**\n"
        "📦 ساخت پک استیکر با نام دلخواه (اجباری)\n"
        "🎨 دو نوع استیکر: ساده و پیشرفته\n"
        "⚙️ تنظیمات کامل متن (اندازه، رنگ، موقعیت)\n"
        "👀 پیش نمایش زنده استیکر\n"
        "🔗 دریافت لینک پک برای نصب و اشتراک‌گذاری\n\n"
        "📊 سهمیه شما در بخش «سهمیه من» قابل مشاهده است"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu()))

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ فقط ادمین!")
        return
    
    text = (
        f"👑 پنل ادمین\n\n"
        f"👥 کاربران: {len(USERS)}\n"
        f"⚡ محدودیت روزانه: {ADVANCED_DAILY_LIMIT}\n"
        f"📊 وضعیت: فعال ✅"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu()))

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
        "📞 **پشتیبانی:**\n"
        f"• ارتباط با ادمین: {SUPPORT_USERNAME}\n\n"
        "📝 **نحوه استفاده:**\n"
        "۱. روی 🎨 استیکر ساز کلیک کنید\n"
        "۲. مینی اپ باز می‌شود\n"
        "۳. نام پک را وارد کنید (اجباری)\n"
        "۴. عکس و متن خود را آپلود کنید\n"
        "۵. تنظیمات را سفارشی کرده و استیکر بسازید\n"
        "۶. لینک پک را برای نصب دریافت کنید"
    )
    
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu()))
    else:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu()))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "sticker_maker":
        keyboard = [
            [InlineKeyboardButton("🎨 باز کردن مینی اپ", web_app=WebAppInfo(url=MINI_APP_URL))],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        
        text = (
            "🎨 **استیکر ساز حرفه‌ای**\n\n"
            "✨ با مینی اپ جدید ما:\n"
            "📦 ساخت پک استیکر با نام دلخواه\n"
            "🎨 استیکر ساده و پیشرفته\n"
            "⚙️ تنظیمات کامل متن (اندازه، رنگ، موقعیت)\n"
            "👀 پیش نمایش زنده استیکر\n"
            "🔗 دریافت لینک پک برای اشتراک‌گذاری\n\n"
            "روی دکمه زیر کلیک کنید تا مینی اپ باز شود:"
        )
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "quota":
        reset_daily_limit(user_id)
        remaining = get_remaining(user_id)
        used = ADVANCED_DAILY_LIMIT - remaining
        
        # Calculate time until reset
        limits = get_limits(user_id)
        try:
            last_reset = datetime.fromisoformat(limits["last_reset"])
            next_reset = last_reset + timedelta(hours=24)
            time_until = next_reset - datetime.now(timezone.utc)
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            time_text = f"🔄 ریست بعد از: {hours} ساعت و {minutes} دقیقه"
        except:
            time_text = "🔄 ریست نامشخص"
        
        text = (
            f"📊 **سهمیه شما**\n\n"
            f"🎨 **استیکر ساده:**\n"
            f"✅ نامحدود\n\n"
            f"⚡ **استیکر پیشرفته:**\n"
            f"📈 استفاده شده: {used} از {ADVANCED_DAILY_LIMIT}\n"
            f"📊 باقی‌مانده: {remaining} استیکر\n"
            f"{time_text}\n\n"
            f"💡 نکته: برای ساخت استیکر پیشرفته، حتماً از مینی اپ استفاده کنید"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "help":
        await help_cmd(update, context)
    
    elif data == "support":
        text = (
            f"📞 **پشتیبانی ربات**\n\n"
            f"👨‍💻 ادمین: {SUPPORT_USERNAME}\n\n"
            "❓ برای سوال و مشکل با ادمین در ارتباط باشید\n"
            f"💬 [{SUPPORT_USERNAME}](https://t.me/{SUPPORT_USERNAME[1:]})"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == "back":
        await query.edit_message_text("🎨 به منوی اصلی بازگشتید:\n\nیک گزینه را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(get_main_menu()))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if "mode" not in session:
        return
    
    try:
        # Get photo
        photo_file = await update.message.photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        session["image"] = photo_bytes
        session["waiting_text"] = True
        
        await update.message.reply_text("✅ عکس دریافت شد!\n\n⚠️ **نکته مهم:** برای امکانات کامل (ساخت پک، تنظیمات پیشرفته، لینک پک) لطفاً از مینی اپ استفاده کنید:\n\n🎨 روی دکمه «استیکر ساز (مینی اپ)» در منوی اصلی کلیک کنید")
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ خطا در دریافت عکس")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if not session.get("waiting_text"):
        return
    
    try:
        text = update.message.text
        image_data = session["image"]
        mode = session["mode"]
        
        await update.message.reply_text("⏳ در حال ساخت استیکر...")
        
        if mode == "simple":
            # Simple sticker - default settings
            sticker_bytes = create_sticker(text, image_data)
        else:
            # Advanced sticker - custom settings
            sticker_bytes = create_sticker(
                text, image_data,
                position_x=256, position_y=200,
                font_size=45, color="#FFFFFF"
            )
            use_advanced(user_id)
        
        if sticker_bytes:
            sticker_file = io.BytesIO(sticker_bytes)
            sticker_file.name = f"sticker_{uuid.uuid4().hex[:8]}.webp"
            
            await update.message.reply_sticker(sticker=sticker_file)
            
            await update.message.reply_text(
                "✅ استیکر ساخته شد!\n\n"
                "⚠️ **برای امکانات کامل:**\n"
                "📦 ساخت پک استیکر\n"
                "⚙️ تنظیمات پیشرفته\n"
                "🔗 لینک پک برای اشتراک‌گذاری\n\n"
                "🎨 از مینی اپ استفاده کنید: روی دکمه «استیکر ساز (مینی اپ)» در منوی اصلی کلیک کنید",
                reply_markup=InlineKeyboardMarkup(get_main_menu())
            )
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر")
        
        # Clear session
        clear_session(user_id)
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        await update.message.reply_text("❌ خطا در ساخت استیکر")
        clear_session(user_id)

# Flask routes
@app.route('/')
def home():
    return "Updated Sticker Bot with Mini App is running!"

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Webhook handler"""
    try:
        if request.is_json:
            update_data = request.get_json()
            update = Update.de_json(update_data, bot.application.bot)
            asyncio.run(bot.application.process_update(update))
            return "OK"
        else:
            return "Invalid request", 400
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

# Bot setup
bot = None

def main():
    """Main function"""
    global bot
    
    # Load data
    load_data()
    
    # Setup bot
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found")
        return
    
    application = Application.builder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    bot = type('Bot', (), {'application': application})()
    
    # Set webhook
    webhook_url = os.environ.get("VERCEL_URL")
    if webhook_url:
        full_url = f"https://{webhook_url}/api/webhook"
        try:
            asyncio.run(application.bot.set_webhook(full_url))
            logger.info("Webhook set successfully")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
    
    # Start Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()