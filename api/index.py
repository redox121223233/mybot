#!/usr/bin/env python3
"""
Advanced Telegram Sticker Bot with User Limits - Fixed Version
Complete bot with simple and advanced modes and proper error handling
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

# Try imports with proper error handling
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
    from telegram.error import BadRequest
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError as e:
    logging.error(f"Telegram library not available: {e}")
    TELEGRAM_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError as e:
    logging.error(f"PIL library not available: {e}")
    PIL_AVAILABLE = False

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT_AVAILABLE = True
except ImportError as e:
    logging.error(f"Arabic support libraries not available: {e}")
    ARABIC_SUPPORT_AVAILABLE = False

try:
    from flask import Flask, request
    FLASK_AVAILABLE = True
except ImportError as e:
    logging.error(f"Flask library not available: {e}")
    FLASK_AVAILABLE = False

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Vercel (if available)
if FLASK_AVAILABLE:
    app = Flask(__name__)
else:
    app = None

# Bot Configuration
ADMIN_ID = 6053579919
SUPPORT_USERNAME = "@onedaytoalive"
ADVANCED_DAILY_LIMIT = 3

# Data Storage
USERS: dict[int, dict] = {}
USER_LIMITS: dict[int, dict] = {}
USER_FILE = "/tmp/users.json"
LIMITS_FILE = "/tmp/user_limits.json"

def load_data():
    """Load user and limit data from files"""
    global USERS, USER_LIMITS
    try:
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r') as f:
                USERS = json.load(f)
        if os.path.exists(LIMITS_FILE):
            with open(LIMITS_FILE, 'r') as f:
                USER_LIMITS = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_users():
    """Save user data"""
    try:
        with open(USER_FILE, 'w') as f:
            json.dump(USERS, f)
    except Exception as e:
        logger.error(f"Failed to save users: {e}")

def save_limits():
    """Save limit data"""
    try:
        with open(LIMITS_FILE, 'w') as f:
            json.dump(USER_LIMITS, f)
    except Exception as e:
        logger.error(f"Failed to save limits: {e}")

def get_user_limits(user_id: int) -> dict:
    """Get or create user limits"""
    if user_id not in USER_LIMITS:
        USER_LIMITS[user_id] = {
            "advanced_used": 0,
            "last_reset": datetime.now(timezone.utc).isoformat(),
            "advanced_count_today": 0
        }
        save_limits()
    
    return USER_LIMITS[user_id]

def reset_daily_limits(user_id: int):
    """Reset daily limits if 24 hours passed"""
    limits = get_user_limits(user_id)
    
    try:
        last_reset = datetime.fromisoformat(limits["last_reset"])
        now = datetime.now(timezone.utc)
        
        # Reset if 24 hours have passed
        if (now - last_reset) >= timedelta(hours=24):
            limits["advanced_count_today"] = 0
            limits["last_reset"] = now.isoformat()
            save_limits()
            logger.info(f"Daily limits reset for user {user_id}")
    except:
        # If there's any error with dates, reset to today
        limits["advanced_count_today"] = 0
        limits["last_reset"] = datetime.now(timezone.utc).isoformat()
        save_limits()

def can_use_advanced(user_id: int) -> bool:
    """Check if user can use advanced mode"""
    reset_daily_limits(user_id)
    limits = get_user_limits(user_id)
    return limits["advanced_count_today"] < ADVANCED_DAILY_LIMIT

def use_advanced_sticker(user_id: int):
    """Increment advanced usage count"""
    limits = get_user_limits(user_id)
    limits["advanced_count_today"] += 1
    save_limits()

def get_remaining_advanced(user_id: int) -> int:
    """Get remaining advanced stickers for today"""
    reset_daily_limits(user_id)
    limits = get_user_limits(user_id)
    return ADVANCED_DAILY_LIMIT - limits["advanced_count_today"]

def create_sticker(text: str, image_data: bytes = None, 
                   position_x: int = 256, position_y: int = 256,
                   font_size: int = 40, text_color: str = "#FFFFFF",
                   font_path: str = None) -> bytes:
    """Create sticker with text and optional image"""
    if not PIL_AVAILABLE:
        logger.error("PIL not available for sticker creation")
        return None
        
    try:
        # Base image
        if image_data:
            img = Image.open(io.BytesIO(image_data))
            img = img.convert('RGBA')
            # Resize to 512x512 maintaining aspect ratio
            img.thumbnail((512, 512), Image.Resampling.LANCZOS)
            
            # Create 512x512 canvas
            canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
            
            # Center the image
            x_offset = (512 - img.width) // 2
            y_offset = (512 - img.height) // 2
            canvas.paste(img, (x_offset, y_offset), img)
            img = canvas
        else:
            # Create gradient background
            img = Image.new('RGB', (512, 512), '#FF6B6B')
            
            # Add gradient effect
            for y in range(512):
                r = int(255 - (y * 50 / 512))
                g = int(107 - (y * 30 / 512))
                b = int(107 - (y * 30 / 512))
                for x in range(512):
                    img.putpixel((x, y), (r, g, b))
        
        draw = ImageDraw.Draw(img)
        
        # Process Arabic/Persian text
        if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
            if ARABIC_SUPPORT_AVAILABLE:
                try:
                    reshaped_text = arabic_reshaper.reshape(text)
                    display_text = get_display(reshaped_text)
                except:
                    display_text = text
            else:
                display_text = text
        else:
            display_text = text
        
        # Load font
        font = None
        font_paths = [
            font_path,
            "fonts/Vazirmatn-Regular.ttf",
            "fonts/IRANSans.ttf",
            "fonts/Sahel.ttf",
            "/System/Library/Fonts/Arial.ttf"
        ]
        
        for path in font_paths:
            if path and os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, font_size)
                    break
                except:
                    continue
        
        if not font:
            font = ImageFont.load_default()
        
        # Get text dimensions
        bbox = draw.textbbox((0, 0), display_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Draw text at specified position
        x = position_x - text_width // 2
        y = position_y - text_height // 2
        
        # Add shadow
        shadow_offset = 2
        draw.text((x + shadow_offset, y + shadow_offset), display_text, font=font, fill="#000000")
        
        # Draw main text
        draw.text((x, y), display_text, font=font, fill=text_color)
        
        # Convert to WebP
        output = io.BytesIO()
        img.save(output, format='WebP', quality=95, optimize=True)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        return None

# Session management
SESSIONS: dict[int, dict] = {}

def get_session(user_id: int) -> dict:
    """Get or create user session"""
    if user_id not in SESSIONS:
        SESSIONS[user_id] = {
            "mode": None,
            "waiting_for": None,
            "sticker_data": {}
        }
    return SESSIONS[user_id]

def reset_session(user_id: int):
    """Reset user session"""
    if user_id in SESSIONS:
        del SESSIONS[user_id]

# Command Handlers (only if telegram is available)
if TELEGRAM_AVAILABLE:
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            reset_session(user_id)
            
            # Create user if not exists
            if user_id not in USERS:
                USERS[user_id] = {
                    "first_name": update.effective_user.first_name,
                    "username": update.effective_user.username,
                    "joined_at": datetime.now(timezone.utc).isoformat()
                }
                save_users()
            
            keyboard = [
                [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_maker")],
                [InlineKeyboardButton("📋 سهمیه من", callback_data="my_quota")],
                [InlineKeyboardButton("📖 راهنما", callback_data="help")],
                [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
            ]
            
            welcome_text = (
                "🎨 به ربات استیکر ساز خوش آمدید!\n\n"
                "✨ با استفاده از این ربات می‌توانید:\n"
                "📍 استیکر ساده و پیشرفته بسازید\n"
                "🔸 استیکر ساده: نامحدود (متن + عکس)\n"
                "⚡ استیکر پیشرفته: ۳ بار در روز (متن + عکس + تنظیمات)\n\n"
                "📊 سهمیه روزانه شما در بخش «سهمیه من» قابل مشاهده است"
            )
            
            await update.message.reply_text(
                welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error in start handler: {e}")
            await update.message.reply_text("❌ خطا در اجرای دستور. لطفا دوباره تلاش کنید.")

    async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin panel"""
        try:
            user_id = update.effective_user.id
            
            if user_id != ADMIN_ID:
                await update.message.reply_text("❌ این دستور فقط برای ادمین ربات است")
                return
            
            total_users = len(USERS)
            today = datetime.now(timezone.utc).date().isoformat()
            
            # Count advanced usage today
            advanced_today = 0
            for uid, limits in USER_LIMITS.items():
                try:
                    last_reset = datetime.fromisoformat(limits["last_reset"])
                    if last_reset.date().isoformat() == today:
                        advanced_today += limits["advanced_count_today"]
                except:
                    pass
            
            admin_text = (
                f"👑 **پنل ادمین**\n\n"
                f"👥 کل کاربران: {total_users}\n"
                f"⚡ استفاده پیشرفته امروز: {advanced_today}\n"
                f"📊 لیمیت روزانه پیشرفته: {ADVANCED_DAILY_LIMIT}\n\n"
                f"🔧 آمار ربات:\n"
                f"• نسخه: 2.0\n"
                f"• وضعیت: فعال ✅"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ]
            
            await update.message.reply_text(
                admin_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in admin panel: {e}")
            await update.message.reply_text("❌ خطا در پنل ادمین")

    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help command"""
        try:
            help_text = (
                "📖 **راهنمای کامل ربات**\n\n"
                "🎨 **دکمه استیکر ساز:**\n"
                "• **ساده**: نامحدود استفاده (فقط متن + عکس)\n"
                "• **پیشرفته**: ۳ بار در روز (متن + عکس + موقعیت + رنگ + اندازه فونت)\n\n"
                "📋 **سهمیه من:**\n"
                "• نمایش تعداد استفاده باقی‌مانده از حالت پیشرفته\n"
                "• نمایش زمان ریست شدن سهمیه\n\n"
                "📞 **پشتیبانی:**\n"
                "• ارتباط با ادمین برای حل مشکلات\n\n"
                "👑 **پنل ادمین** (فقط برای ادمین):\n"
                "• مشاهده آمار کامل ربات\n\n"
                "📝 **نحوه استفاده:**\n"
                "۱. روی 🎨 استیکر ساز کلیک کنید\n"
                "۲. حالت ساده یا پیشرفته را انتخاب کنید\n"
                "۳. عکس خود را ارسال کنید\n"
                "۴. متن دلخواه را بنویسید\n"
                "۵. در حالت پیشرفته، تنظیمات را مشخص کنید"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
            ]
            
            if update.message:
                await update.message.reply_text(
                    help_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.callback_query.message.reply_text(
                    help_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await update.message.reply_text("❌ خطا در نمایش راهنما")

    async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            callback_data = query.data
            
            if callback_data == "sticker_maker":
                keyboard = [
                    [InlineKeyboardButton("🎨 استیکر ساده", callback_data="simple_sticker")],
                    [InlineKeyboardButton("⚡ استیکر پیشرفته", callback_data="advanced_sticker")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
                ]
                
                text = (
                    "🎨 **نوع استیکر را انتخاب کنید:**\n\n"
                    "📍 **استیکر ساده:**\n"
                    "✅ نامحدود استفاده\n"
                    "📝 فقط متن + عکس\n\n"
                    "⚡ **استیکر پیشرفته:**\n"
                    "🔸 ۳ بار در روز\n"
                    "📝 متن + عکس + تنظیمات کامل"
                )
                
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            
            elif callback_data == "simple_sticker":
                session = get_session(user_id)
                session["mode"] = "simple"
                session["waiting_for"] = "image"
                
                await query.edit_message_text(
                    "🎨 **استیکر ساده**\n\n"
                    "📸 لطفا عکس مورد نظر خود را ارسال کنید",
                    parse_mode='Markdown'
                )
            
            elif callback_data == "advanced_sticker":
                if not can_use_advanced(user_id):
                    remaining = get_remaining_advanced(user_id)
                    await query.edit_message_text(
                        f"⚠️ **سهمیه پیشرفته تمام شده**\n\n"
                        f"📊 شما امروز {ADVANCED_DAILY_LIMIT} استیکر پیشرفته ساخته‌اید\n"
                        f"🔄 سهمیه شما ۲۴ ساعت دیگر ریست می‌شود\n\n"
                        f"🎨 می‌توانید از استیکر ساده (نامحدود) استفاده کنید",
                        parse_mode='Markdown'
                    )
                    return
                
                session = get_session(user_id)
                session["mode"] = "advanced"
                session["waiting_for"] = "image"
                session["sticker_data"] = {
                    "position_x": 256,
                    "position_y": 256,
                    "font_size": 40,
                    "text_color": "#FFFFFF"
                }
                
                remaining = get_remaining_advanced(user_id)
                await query.edit_message_text(
                    f"⚡ **استیکر پیشرفته**\n\n"
                    f"📊 سهمیه باقی‌مانده: {remaining} از {ADVANCED_DAILY_LIMIT}\n\n"
                    f"📸 لطفا عکس مورد نظر خود را ارسال کنید",
                    parse_mode='Markdown'
                )
            
            elif callback_data == "my_quota":
                reset_daily_limits(user_id)
                limits = get_user_limits(user_id)
                remaining = get_remaining_advanced(user_id)
                
                try:
                    last_reset = datetime.fromisoformat(limits["last_reset"])
                    next_reset = last_reset + timedelta(hours=24)
                    time_until_reset = next_reset - datetime.now(timezone.utc)
                    
                    if time_until_reset.total_seconds() > 0:
                        hours = int(time_until_reset.total_seconds() // 3600)
                        minutes = int((time_until_reset.total_seconds() % 3600) // 60)
                        reset_text = f"🔄 ریست بعد از: {hours} ساعت و {minutes} دقیقه"
                    else:
                        reset_text = "🔄 آماده ریست"
                except:
                    reset_text = "🔄 نامشخص"
                
                quota_text = (
                    f"📊 **سهمیه شما**\n\n"
                    f"🎨 **استیکر ساده:**\n"
                    f"✅ نامحدود\n\n"
                    f"⚡ **استیکر پیشرفته:**\n"
                    f"📈 استفاده شده: {limits['advanced_count_today']} از {ADVANCED_DAILY_LIMIT}\n"
                    f"📊 باقی‌مانده: {remaining} استیکر\n"
                    f"{reset_text}\n\n"
                    f"💡 نکته: سهمیه هر ۲۴ ساعت به صورت خودکار ریست می‌شود"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
                ]
                
                await query.edit_message_text(
                    quota_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            
            elif callback_data == "support":
                support_text = (
                    "📞 **پشتیبانی ربات**\n\n"
                    f"👨‍💻 ادمین: {SUPPORT_USERNAME}\n\n"
                    "🔹 برای هرگونه سوال یا مشکل می‌توانید به ادمین پیام دهید\n"
                    f"💬 کلیک کنید برای ارتباط: [{SUPPORT_USERNAME}](https://t.me/{SUPPORT_USERNAME[1:]})"
                )
                
                keyboard = [
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
                ]
                
                await query.edit_message_text(
                    support_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            
            elif callback_data == "help":
                await help_command(update, context)
            
            elif callback_data == "back_to_main":
                keyboard = [
                    [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_maker")],
                    [InlineKeyboardButton("📋 سهمیه من", callback_data="my_quota")],
                    [InlineKeyboardButton("📖 راهنما", callback_data="help")],
                    [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
                ]
                
                await query.edit_message_text(
                    "🎨 به منوی اصلی بازگشتید!\n\n"
                    "یک گزینه را انتخاب کنید:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
            try:
                await update.callback_query.answer("❌ خطا در اجرای دستور")
            except:
                pass

    async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages"""
        try:
            user_id = update.effective_user.id
            session = get_session(user_id)
            
            if session.get("waiting_for") != "image":
                return
            
            # Get photo file
            photo_file = await update.message.photo.get_file()
            
            # Download photo
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Save to temp file
            temp_image = io.BytesIO(photo_bytes)
            
            # Save image path in session
            session["image_data"] = temp_image.getvalue()
            session["waiting_for"] = "text"
            
            await update.message.reply_text(
                "✅ عکس دریافت شد!\n\n"
                "📝 حالا متن مورد نظر خود را بنویسید:"
            )
        except Exception as e:
            logger.error(f"Error handling photo: {e}")
            await update.message.reply_text("❌ خطا در پردازش عکس. لطفا دوباره تلاش کنید")

    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            user_id = update.effective_user.id
            session = get_session(user_id)
            
            if session.get("waiting_for") != "text":
                return
            
            text = update.message.text
            session["text"] = text
            
            mode = session.get("mode")
            
            if mode == "simple":
                await create_simple_sticker(update, context)
            elif mode == "advanced":
                # For now, create advanced sticker directly
                await create_advanced_sticker(update, context)
        except Exception as e:
            logger.error(f"Error handling text: {e}")
            await update.message.reply_text("❌ خطا در پردازش متن. لطفا دوباره تلاش کنید")

    async def create_simple_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create simple sticker"""
        try:
            user_id = update.effective_user.id
            session = get_session(user_id)
            
            await update.message.reply_text("⏳ در حال ساخت استیکر...")
            
            sticker_bytes = create_sticker(
                text=session["text"],
                image_data=session["image_data"]
            )
            
            if sticker_bytes:
                sticker_file = io.BytesIO(sticker_bytes)
                sticker_file.name = f"sticker_{uuid.uuid4().hex[:8]}.webp"
                
                # Show main menu again
                keyboard = [
                    [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_maker")],
                    [InlineKeyboardButton("📋 سهمیه من", callback_data="my_quota")],
                    [InlineKeyboardButton("📖 راهنما", callback_data="help")],
                    [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
                ]
                
                await update.message.reply_sticker(sticker=sticker_file)
                await update.message.reply_text(
                    "✅ استیکر ساده شما با موفقیت ساخته شد!\n\n"
                    "🎨 برای ساخت استیکر جدید از منو استفاده کنید",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ خطا در ساخت استیکر. لطفا دوباره تلاش کنید")
        
        except Exception as e:
            logger.error(f"Error creating simple sticker: {e}")
            await update.message.reply_text("❌ خطا در ساخت استیکر")
        
        # Reset session
        reset_session(user_id)

    async def create_advanced_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create advanced sticker"""
        try:
            user_id = update.effective_user.id
            session = get_session(user_id)
            
            if not can_use_advanced(user_id):
                await update.message.reply_text("⚠️ سهمیه پیشرفته شما تمام شده است!")
                return
            
            await update.message.reply_text("⏳ در حال ساخت استیکر پیشرفته...")
            
            sticker_bytes = create_sticker(
                text=session["text"],
                image_data=session["image_data"],
                position_x=session["sticker_data"]["position_x"],
                position_y=session["sticker_data"]["position_y"],
                font_size=session["sticker_data"]["font_size"],
                text_color=session["sticker_data"]["text_color"]
            )
            
            if sticker_bytes:
                sticker_file = io.BytesIO(sticker_bytes)
                sticker_file.name = f"sticker_{uuid.uuid4().hex[:8]}.webp"
                
                # Use advanced sticker usage
                use_advanced_sticker(user_id)
                
                # Show main menu again
                keyboard = [
                    [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_maker")],
                    [InlineKeyboardButton("📋 سهمیه من", callback_data="my_quota")],
                    [InlineKeyboardButton("📖 راهنما", callback_data="help")],
                    [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
                ]
                
                await update.message.reply_sticker(sticker=sticker_file)
                await update.message.reply_text(
                    "✅ استیکر پیشرفته شما با موفقیت ساخته شد!\n\n"
                    f"📊 سهمیه باقی‌مانده: {get_remaining_advanced(user_id)} از {ADVANCED_DAILY_LIMIT}\n\n"
                    "🎨 برای ساخت استیکر جدید از منو استفاده کنید",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text("❌ خطا در ساخت استیکر. لطفا دوباره تلاش کنید")
        
        except Exception as e:
            logger.error(f"Error creating advanced sticker: {e}")
            await update.message.reply_text("❌ خطا در ساخت استیکر")
        
        # Reset session
        reset_session(user_id)

# Flask routes for Vercel
if app:
    @app.route('/')
    def home():
        return "Advanced Telegram Sticker Bot is running!"

    @app.route('/api/webhook', methods=['POST'])
    def webhook():
        """Handle webhook requests from Telegram"""
        try:
            if not TELEGRAM_AVAILABLE:
                return "Telegram library not available", 500
                
            if request.is_json:
                update_data = request.get_json()
                
                # Create Update object from JSON
                update = Update.de_json(update_data, bot.application.bot)
                
                # Process the update
                asyncio.run(bot.application.process_update(update))
                
                return "OK"
            else:
                return "Invalid request", 400
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return "Error", 500

# Global bot instance
bot = None

def main():
    """Main function to run the bot"""
    global bot
    
    # Load existing data
    load_data()
    
    # Check dependencies
    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram library not available. Bot cannot start.")
        return
    
    # Setup bot
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
    try:
        application = Application.builder().token(bot_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("help", help_command))
        
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        bot = type('Bot', (), {'application': application})()
        
        # Set webhook for Vercel deployment
        webhook_url = os.environ.get("VERCEL_URL")
        
        if bot_token and webhook_url:
            full_webhook_url = f"https://{webhook_url}/api/webhook"
            logger.info(f"Setting webhook to: {full_webhook_url}")
            
            try:
                asyncio.run(application.bot.set_webhook(full_webhook_url))
                logger.info("Webhook set successfully")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")
        
        # Start Flask app if available
        if app:
            port = int(os.environ.get("PORT", 5000))
            app.run(host="0.0.0.0", port=port)
        else:
            logger.error("Flask not available. Cannot start web server")
            
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()