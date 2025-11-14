#!/usr/bin/env python3
"""
Simple Telegram Sticker Bot - Fixed Version for Vercel
Exactly as requested: 4 buttons only, simple and working
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

def create_advanced_sticker(text: str, image_data: bytes, 
                           position_x: int = 256, position_y: int = 256,
                           font_size: int = 40, color: str = "#FFFFFF") -> bytes:
    """Create advanced sticker"""
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
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        if not font:
            font = ImageFont.load_default()
        
        # Get text dimensions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position text
        x = position_x - text_width // 2
        y = position_y - text_height // 2
        
        # Add shadow
        draw.text((x+2, y+2), text, font=font, fill="#000000")
        
        # Draw main text
        draw.text((x, y), text, font=font, fill=color)
        
        # Save as WebP
        output = io.BytesIO()
        canvas.save(output, format='WebP', quality=95)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating advanced sticker: {e}")
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
def get_main_menu(webapp_url=None):
    """Get main menu keyboard"""
    buttons = []
    
    # Add Mini App button first if available
    if webapp_url:
        buttons.append([InlineKeyboardButton("🚀 باز کردن Mini App", web_app=WebAppInfo(url=webapp_url))])
    
    # Add regular buttons
    buttons.extend([
        [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_maker")],
        [InlineKeyboardButton("📊 سهمیه من", callback_data="quota")],
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
    ])
    
    return buttons

# Global application
application = None

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
    
    # Get webapp URL from environment or use default
    webapp_url = os.environ.get("WEBAPP_URL", None)
    
    text = (
        "🎨 به ربات استیکر ساز خوش آمدید!\n\n"
        "✨ ویژگی‌ها:\n"
        "📍 استیکر ساده: نامحدود (عکس + متن)\n"
        "⚡ استیکر پیشرفته: ۳ بار در روز (عکس + متن + تنظیمات)\n\n"
    )
    
    if webapp_url:
        text += "🚀 می‌توانید از Mini App هم استفاده کنید!\n\n"
    
    text += "📊 سهمیه شما در بخش «سهمیه من» قابل مشاهده است"
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu(webapp_url)))

async def webapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open Mini App directly"""
    webapp_url = os.environ.get("WEBAPP_URL", None)
    
    if not webapp_url:
        await update.message.reply_text(
            "❌ Mini App هنوز فعال نشده!\n\n"
            "لطفاً از دکمه‌های زیر استفاده کنید:",
            reply_markup=InlineKeyboardMarkup(get_main_menu())
        )
        return
    
    keyboard = [[InlineKeyboardButton("🚀 باز کردن Mini App", web_app=WebAppInfo(url=webapp_url))]]
    
    await update.message.reply_text(
        "🎨 Mini App استیکر ساز\n\n"
        "روی دکمه زیر کلیک کنید تا Mini App باز شود:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ فقط ادمین!")
        return
    
    webapp_url = os.environ.get("WEBAPP_URL", "Not set")
    
    text = (
        f"👹 پنل ادمین\n\n"
        f"👥 کاربران: {len(USERS)}\n"
        f"⚡ limite روزانه: {ADVANCED_DAILY_LIMIT}\n"
        f"🌐 Mini App: {webapp_url}\n"
        f"🎬 وضعیت: فعال ✅"
    )
    
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(get_main_menu(webapp_url)))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    text = (
        "📖 راهنمای ربات\n\n"
        "🎨 **استیکر ساز:**\n"
        "• ساده: نامحدود، فقط عکس + متن\n"
        "• پیشرفته: ۳ بار در روز، با تنظیمات کامل\n\n"
        "📊 **سهمیه من:**\n"
        "• نمایش تعداد استیکر پیشرفته باقی‌مانده\n"
        "• نمایش زمان تا ریست شدن سهمیه\n\n"
        "📞 **پشتیبانی:**\n"
        f"• تماس با ادمین: {SUPPORT_USERNAME}\n\n"
        "📝 **نحوه استفاده:**\n"
        "۱. استیکر ساز → ساده یا پیشرفته\n"
        "۲. ارسال عکس\n"
        "۳. نوشتن متن\n"
        "۴. دریافت استیکر"
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
            [InlineKeyboardButton("🎨 استیکر ساده", callback_data="simple")],
            [InlineKeyboardButton("⚡ استیکر پیشرفته", callback_data="advanced")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        
        text = (
            "🎨 نوع استیکر را انتخاب کنید:\n\n"
            "📍 **ساده:** نامحدود استفاده\n"
            "   فقط عکس + متن\n\n"
            "⚡ **پیشرفته:** ۳ بار در روز\n"
            "   عکس + متن + تنظیمات"
        )
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "simple":
        session = get_session(user_id)
        session["mode"] = "simple"
        await query.edit_message_text("🎨 استیکر ساده\n\n📷 عکس خود را ارسال کنید:")
    
    elif data == "advanced":
        if not can_use_advanced(user_id):
            await query.edit_message_text("⚠️ سهمیه پیشرفته تمام شده!\n\n📍 می‌توانید از استیکر ساده استفاده کنید")
            return
        
        session = get_session(user_id)
        session["mode"] = "advanced"
        remaining = get_remaining(user_id)
        
        # Show advanced options
        keyboard = [
            [InlineKeyboardButton("📍 موقعیت متن", callback_data="adv_position")],
            [InlineKeyboardButton("🌈 رنگ متن", callback_data="adv_color")],
            [InlineKeyboardButton("📏 اندازه فونت", callback_data="adv_size")],
            [InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        
        text = (
            f"⚡ استیکر پیشرفته\n\n"
            f"📊 سهمیه: {remaining} از {ADVANCED_DAILY_LIMIT}\n\n"
            f"⚙️ تنظیمات استیکر:"
        )
        
        session["text"] = None
        session["image"] = None
        session["position"] = (256, 256)
        session["color"] = "#FFFFFF"
        session["font_size"] = 40
        
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
            f"📊 سهمیه شما\n\n"
            f"🎨 **استیکر ساده:**\n"
            f"✅ نامحدود\n\n"
            f"⚡ **استیکر پیشرفته:**\n"
            f"📈 استفاده شده: {used} از {ADVANCED_DAILY_LIMIT}\n"
            f"📊 باقی‌مانده: {remaining} استیکر\n"
            f"{time_text}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "help":
        await help_cmd(update, context)
    
    elif data == "support":
        text = (
            f"📞 پشتیبانی ربات\n\n"
            f"👨‍💻 ادمین: {SUPPORT_USERNAME}\n\n"
            "👹 برای سوال و مشکل با ادمین در ارتباط باشید\n"
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
        
        if session["mode"] == "simple":
            await update.message.reply_text("✅ عکس دریافت شد!\n\n📝 متن خود را بنویسید:")
        else:
            await update.message.reply_text("✅ عکس دریافت شد!\n\n📝 متن خود را بنویسید:")
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ خطا در دریافت عکس")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if "mode" not in session or not session.get("image"):
        return
    
    try:
        text = update.message.text
        image_data = session["image"]
        mode = session["mode"]
        
        await update.message.reply_text("⏳ در حال ساخت استیکر...")
        
        if mode == "simple":
            sticker_bytes = create_sticker(text, image_data)
        else:
            # For advanced, store text and show options again
            session["text"] = text
            
            remaining = get_remaining(user_id)
            keyboard = [
                [InlineKeyboardButton("📍 موقعیت متن", callback_data="adv_position")],
                [InlineKeyboardButton("🌈 رنگ متن", callback_data="adv_color")],
                [InlineKeyboardButton("📏 اندازه فونت", callback_data="adv_size")],
                [InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
            ]
            
            await update.message.reply_text(
                f"⚡ استیکر پیشرفته\n\n"
                f"📝 متن: {text}\n\n"
                f"📊 سهمیه: {remaining} از {ADVANCED_DAILY_LIMIT}\n\n"
                f"⚙️ تنظیمات استیکر:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        if sticker_bytes:
            sticker_file = io.BytesIO(sticker_bytes)
            sticker_file.name = f"sticker_{uuid.uuid4().hex[:8]}.webp"
            
            await update.message.reply_sticker(sticker=sticker_file)
            
            await update.message.reply_text(
                "✅ استیکر ساده ساخته شد!\n\n"
                "🎨 برای استیکر جدید از منو استفاده کنید",
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

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data from Mini App"""
    try:
        user_id = update.effective_user.id
        
        # Get data from web_app_data
        if update.message and update.message.web_app_data:
            data_string = update.message.web_app_data.data
            data = json.loads(data_string)
            
            action = data.get("action", "unknown")
            
            logger.info(f"Received webapp data from {user_id}: {action}")
            
            # Handle different actions
            if action == "create_sticker":
                await update.message.reply_text(
                    "🎨 عالی! بیا استیکر بسازیم!\n\n"
                    "📷 لطفاً عکس خود را ارسال کنید:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
                )
                session = get_session(user_id)
                session["mode"] = "simple"
                
            elif action == "view_gallery":
                await update.message.reply_text(
                    "⭐ گالری استیکرهای شما\n\n"
                    "💡 در حال حاضر این قابلیت در دست توسعه است.\n"
                    "به زودی می‌توانید تمام استیکرهای خود را مشاهده کنید!",
                    reply_markup=InlineKeyboardMarkup(get_main_menu())
                )
                
            elif action == "chat":
                await update.message.reply_text(
                    "💬 سلام! چطور می‌تونم کمکت کنم؟\n\n"
                    "من می‌تونم برات:\n"
                    "🎨 استیکر بسازم\n"
                    "⚡ استیکر پیشرفته با تنظیمات کامل\n"
                    "📊 سهمیه‌ات رو نشون بدم",
                    reply_markup=InlineKeyboardMarkup(get_main_menu())
                )
                
            elif action == "quick_sticker" or action == "gallery":
                await update.message.reply_text(
                    f"🎯 درخواست «{action}» دریافت شد!\n\n"
                    "📷 برای شروع، عکس خود را ارسال کنید:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
                )
                session = get_session(user_id)
                session["mode"] = "simple"
                
            elif action == "main_button" or action == "main_button_clicked":
                await update.message.reply_text(
                    "✅ دکمه اصلی فشرده شد!\n\n"
                    "از منوی زیر یک گزینه را انتخاب کنید:",
                    reply_markup=InlineKeyboardMarkup(get_main_menu())
                )
                
            # Handle Persian action names
            elif action == "ساخت استیکر":
                await update.message.reply_text(
                    "🎨 عالی! بیا استیکر بسازیم!\n\n"
                    "📷 لطفاً عکس خود را ارسال کنید:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
                )
                session = get_session(user_id)
                session["mode"] = "simple"
                
            elif action == "چت هوشمند":
                await update.message.reply_text(
                    "💬 سلام! چطور می‌تونم کمکت کنم؟\n\n"
                    "من می‌تونم برات:\n"
                    "🎨 استیکر بسازم\n"
                    "⚡ استیکر پیشرفته با تنظیمات کامل\n"
                    "📊 سهمیه‌ات رو نشون بدم",
                    reply_markup=InlineKeyboardMarkup(get_main_menu())
                )
                
            elif action == "سریع و آسان":
                await update.message.reply_text(
                    "⚡ استیکر سریع!\n\n"
                    "📷 عکس خود را ارسال کنید تا سریع استیکر بسازم:",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
                )
                session = get_session(user_id)
                session["mode"] = "simple"
                
            elif action == "کیفیت بالا":
                # Check if can use advanced
                if can_use_advanced(user_id):
                    await update.message.reply_text(
                        "⭐ استیکر با کیفیت بالا!\n\n"
                        "📷 عکس خود را ارسال کنید:",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]])
                    )
                    session = get_session(user_id)
                    session["mode"] = "advanced"
                else:
                    remaining = get_remaining(user_id)
                    await update.message.reply_text(
                        f"⚠️ سهمیه پیشرفته تمام شده!\n\n"
                        f"📊 سهمیه شما: {remaining} از {ADVANCED_DAILY_LIMIT}\n"
                        f"💡 می‌توانید از استیکر ساده استفاده کنید",
                        reply_markup=InlineKeyboardMarkup(get_main_menu())
                    )
                
            else:
                await update.message.reply_text(
                    f"✅ درخواست «{action}» دریافت شد!\n\n"
                    "از منوی زیر ادامه دهید:",
                    reply_markup=InlineKeyboardMarkup(get_main_menu())
                )
                
    except Exception as e:
        logger.error(f"Error handling webapp data: {e}")
        await update.message.reply_text(
            "❌ خطا در پردازش درخواست\n\n"
            "لطفاً دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup(get_main_menu())
        )

# Initialize bot
def init_bot():
    """Initialize bot application"""
    global application
    
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
    application.add_handler(CommandHandler("webapp", webapp_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Initialize the application only
    asyncio.run(application.initialize())
    logger.info("Bot application initialized successfully")
    return application

# Vercel Handler Class - Required for Vercel Python deployment
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    """Vercel Python handler class that inherits from BaseHTTPRequestHandler"""
    
    def do_GET(self):
        """Handle GET requests"""
        try:
               # Try to serve the mini app HTML file
               try:
                   with open("public/index.html", "r", encoding="utf-8") as f:
                       html_content = f.read()
                       
                   self.send_response(200)
                   self.send_header("Content-type", "text/html; charset=utf-8")
                   self.end_headers()
                   self.wfile.write(html_content.encode("utf-8"))
                   
               except FileNotFoundError:
                   # Fallback to JSON if HTML file not found
                   self.send_response(200)
                   self.send_header("Content-type", "application/json")
                   self.end_headers()
                   
                   # Get webapp URL
                   webapp_url = os.environ.get("WEBAPP_URL", None)
                   
                   response = {
                       "status": "ok", 
                       "message": "Sticker Bot is running!",
                       "users": len(USERS),
                       "web_app": webapp_url if webapp_url else "Not configured"
                   }
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
        try:
            # Initialize bot if not already done
            global application
            if application is None:
                application = init_bot()
                if application is None:
                    # BOT_TOKEN not found, return error
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response = {"status": "error", "message": "BOT_TOKEN not configured"}
                    self.wfile.write(json.dumps(response).encode())
                    return
            
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            if post_data:
                # Parse JSON data
                data = json.loads(post_data.decode('utf-8'))
                
                # Create a new application instance for this request
                bot_token = os.environ.get("BOT_TOKEN")
                if bot_token:
                    temp_app = Application.builder().token(bot_token).build()
                    asyncio.run(temp_app.initialize())
                    
                    # Process Telegram update
                    update = Update.de_json(data, temp_app.bot)
                    
                    # Add handlers temporarily
                    temp_app.add_handler(CommandHandler("start", start))
                    temp_app.add_handler(CommandHandler("admin", admin))
                    temp_app.add_handler(CommandHandler("help", help_cmd))
                    temp_app.add_handler(CommandHandler("webapp", webapp_command))
                    temp_app.add_handler(CallbackQueryHandler(button_callback))
                    temp_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
                    temp_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
                    temp_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
                    
                    asyncio.run(temp_app.start())
                    asyncio.run(temp_app.process_update(update))
                    asyncio.run(temp_app.stop())
                
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
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response).encode())

# Initialize only when needed (not on import)
# init_bot()  # Commented out to prevent auto-initialization on Vercel
