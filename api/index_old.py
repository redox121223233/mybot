#!/usr/bin/env python3
"""
Advanced Telegram Sticker Bot with User Limits
Complete bot with simple and advanced modes
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

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.error import BadRequest
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
            try:
                reshaped_text = arabic_reshaper.reshape(text)
                display_text = get_display(reshaped_text)
            except:
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

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
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

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel"""
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
        [InlineKeyboardButton("📊 آمار کامل", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ]
    
    await update.message.reply_text(
        admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help command"""
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
        "• مشاهده آمار کامل ربات\n"
        "• مدیریت کاربران و سهمیه‌ها\n\n"
        "📝 **نحوه استفاده:**\n"
        "۱. روی 🎨 استیکر ساز کلیک کنید\n"
        "۲. حالت ساده یا پیشرفته را انتخاب کنید\n"
        "۳. عکس خود را ارسال کنید\n"
        "۴. متن دلخواه را بنویسید\n"
        "۵. در حالت پیشرفته، تنظیمات را مشخص کنید\n\n"
        "⚡ **نکات مهم:**\n"
        "• هر عکس باید کمتر از ۱۰ مگابایت باشد\n"
        "• از فرمت‌های JPG, PNG پشتیبانی می‌شود\n"
        "• متن فارسی و انگلیسی پشتیبانی می‌شود\n"
        "• سهمیه پیشرفته هر ۲۴ ساعت ریست می‌شود"
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

# Callback Query Handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "sticker_maker":
        # Show sticker maker options
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
            "📝 متن + عکس + تنظیمات کامل\n"
            "   • موقعیت متن\n"
            "   • رنگ متن\n"
            "   • اندازه فونت"
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
            "📸 لطفا عکس مورد نظر خود را ارسال کنید\n"
            "(میتوانید از گالری انتخاب کنید یا عکس جدید بگیرید)",
            parse_mode='Markdown'
        )
    
    elif callback_data == "advanced_sticker":
        # Check if user can use advanced mode
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
            "🔹 مشکلات فنی و پیشنهادات خود را با ما در میان بگذارید\n"
            "🔹 پاسخگویی در سریع‌ترین زمان ممکن\n\n"
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
    
    elif callback_data.startswith("adv_"):
        await handle_advanced_options(update, context)
    
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

async def handle_advanced_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle advanced sticker options"""
    query = update.callback_query
    user_id = update.effective_user.id
    session = get_session(user_id)
    callback_data = query.data
    
    if callback_data == "adv_color":
        keyboard = [
            [InlineKeyboardButton("⚪ سفید", callback_data="color_#FFFFFF")],
            [InlineKeyboardButton("⚫ مشکی", callback_data="color_#000000")],
            [InlineKeyboardButton("🔴 قرمز", callback_data="color_#FF0000")],
            [InlineKeyboardButton("🔵 آبی", callback_data="color_#0000FF")],
            [InlineKeyboardButton("🟢 سبز", callback_data="color_#00FF00")],
            [InlineKeyboardButton("🟡 زرد", callback_data="color_#FFFF00")],
            [InlineKeyboardButton("🟣 بنفش", callback_data="color_#FF00FF")],
            [InlineKeyboardButton("🟠 نارنجی", callback_data="color_#FFA500")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_advanced")]
        ]
        
        current_color = session["sticker_data"].get("text_color", "#FFFFFF")
        await query.edit_message_text(
            f"🎨 **انتخاب رنگ متن**\n\n"
            f"رنگ فعیل: {current_color}\n\n"
            f"رنگ جدید را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif callback_data == "adv_size":
        keyboard = [
            [InlineKeyboardButton("🔹 کوچک (30)", callback_data="size_30")],
            [InlineKeyboardButton("🔸 متوسط (40)", callback_data="size_40")],
            [InlineKeyboardButton("🔺 بزرگ (50)", callback_data="size_50")],
            [InlineKeyboardButton("🔻 خیلی بزرگ (60)", callback_data="size_60")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_advanced")]
        ]
        
        current_size = session["sticker_data"].get("font_size", 40)
        await query.edit_message_text(
            f"📏 **انتخاب اندازه فونت**\n\n"
            f"اندازه فعلی: {current_size}\n\n"
            f"اندازه جدید را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif callback_data == "adv_position":
        keyboard = [
            [InlineKeyboardButton("⬆️ بالا", callback_data="pos_top")],
            [InlineKeyboardButton("⬅️ چپ", callback_data="pos_left")],
            [InlineKeyboardButton("⭕ مرکز", callback_data="pos_center")],
            [InlineKeyboardButton("➡️ راست", callback_data="pos_right")],
            [InlineKeyboardButton("⬇️ پایین", callback_data="pos_bottom")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_advanced")]
        ]
        
        await query.edit_message_text(
            "📍 **انتخاب موقعیت متن**\n\n"
            "موقعیت متن روی عکس را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif callback_data == "adv_create":
        await create_advanced_sticker(update, context)
    
    elif callback_data.startswith("color_"):
        color = callback_data.split("_")[1]
        session["sticker_data"]["text_color"] = color
        await query.edit_message_text(
            f"✅ رنگ متن به {color} تغییر کرد\n\n"
            f"برای ساخت استیکر روی «✅ ساخت استیکر» کلیک کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_advanced")]
            ])
        )
    
    elif callback_data.startswith("size_"):
        size = int(callback_data.split("_")[1])
        session["sticker_data"]["font_size"] = size
        await query.edit_message_text(
            f"✅ اندازه فونت به {size} تغییر کرد\n\n"
            f"برای ساخت استیکر روی «✅ ساخت استیکر» کلیک کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_advanced")]
            ])
        )
    
    elif callback_data.startswith("pos_"):
        position = callback_data.split("_")[1]
        positions = {
            "top": (256, 100),
            "left": (100, 256),
            "center": (256, 256),
            "right": (412, 256),
            "bottom": (256, 412)
        }
        
        if position in positions:
            session["sticker_data"]["position_x"] = positions[position][0]
            session["sticker_data"]["position_y"] = positions[position][1]
            
            position_names = {
                "top": "بالا",
                "left": "چپ",
                "center": "مرکز",
                "right": "راست",
                "bottom": "پایین"
            }
            
            await query.edit_message_text(
                f"✅ موقعیت متن به {position_names[position]} تغییر کرد\n\n"
                f"برای ساخت استیکر روی «✅ ساخت استیکر» کلیک کنید",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_advanced")]
                ])
            )
    
    elif callback_data == "back_to_advanced":
        await show_advanced_options_for_message(update, context)

async def show_advanced_options_for_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show advanced options for message"""
    keyboard = [
        [InlineKeyboardButton("🎨 رنگ متن", callback_data="adv_color")],
        [InlineKeyboardButton("📏 اندازه فونت", callback_data="adv_size")],
        [InlineKeyboardButton("📍 موقعیت متن", callback_data="adv_position")],
        [InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ]
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "⚡ **تنظیمات پیشرفته استیکر**\n\n"
            "تنظیمات مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚡ **تنظیمات پیشرفته استیکر**\n\n"
            "تنظیمات مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def create_advanced_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create advanced sticker"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if not can_use_advanced(user_id):
        await update.callback_query.edit_message_text(
            "⚠️ سهمیه پیشرفته شما تمام شده است!"
        )
        return
    
    if update.callback_query:
        await update.callback_query.edit_message_text("⏳ در حال ساخت استیکر پیشرفته...")
    else:
        await update.message.reply_text("⏳ در حال ساخت استیکر پیشرفته...")
    
    try:
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
            
            if update.callback_query:
                await update.callback_query.message.reply_sticker(sticker=sticker_file)
                await update.callback_query.message.reply_text(
                    "✅ استیکر پیشرفته شما با موفقیت ساخته شد!\n\n"
                    f"📊 سهمیه باقی‌مانده: {get_remaining_advanced(user_id)} از {ADVANCED_DAILY_LIMIT}\n\n"
                    "🎨 برای ساخت استیکر جدید از منو استفاده کنید",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_sticker(sticker=sticker_file)
                await update.message.reply_text(
                    "✅ استیکر پیشرفته شما با موفقیت ساخته شد!\n\n"
                    f"📊 سهمیه باقی‌مانده: {get_remaining_advanced(user_id)} از {ADVANCED_DAILY_LIMIT}\n\n"
                    "🎨 برای ساخت استیکر جدید از منو استفاده کنید",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            if update.callback_query:
                await update.callback_query.edit_message_text("❌ خطا در ساخت استیکر. لطفا دوباره تلاش کنید")
            else:
                await update.message.reply_text("❌ خطا در ساخت استیکر. لطفا دوباره تلاش کنید")
    
    except Exception as e:
        logger.error(f"Error creating advanced sticker: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ خطا در ساخت استیکر")
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر")
    
    # Reset session
    reset_session(user_id)

# Message Handlers
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
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

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if session.get("waiting_for") != "text":
        return
    
    text = update.message.text
    session["text"] = text
    
    mode = session.get("mode")
    
    if mode == "simple":
        # Create simple sticker
        await create_simple_sticker(update, context)
    
    elif mode == "advanced":
        # Show advanced options
        await show_advanced_options(update, context)

async def create_simple_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create simple sticker"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    await update.message.reply_text("⏳ در حال ساخت استیکر...")
    
    try:
        sticker_bytes = create_sticker(
            text=session["text"],
            image_data=session["image_data"]
        )
        
        if sticker_bytes:
            sticker_file = io.BytesIO(sticker_bytes)
            sticker_file.name = f"sticker_{uuid.uuid4().hex[:8]}.webp"
            
            await update.message.reply_sticker(sticker=sticker_file)
            
            # Show main menu again
            keyboard = [
                [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_maker")],
                [InlineKeyboardButton("📋 سهمیه من", callback_data="my_quota")],
                [InlineKeyboardButton("📖 راهنما", callback_data="help")],
                [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
            ]
            
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

async def show_advanced_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show advanced sticker options"""
    await show_advanced_options_for_message(update, context)

# Flask routes for Vercel
@app.route('/')
def home():
    return "Advanced Telegram Sticker Bot is running!"

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Handle webhook requests from Telegram"""
    try:
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
    
    # Setup bot
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
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
    
    # Start Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main() < ADVANCED_DAILY_LIMIT

def use_advanced_sticker(user_id: int):
    """Mark that user used advanced mode"""
    limits = get_user_limits(user_id)
    limits["advanced_count_today"] += 1
    save_limits()

def create_webp_sticker(text: str, font_path: str = None, font_size: int = 40, 
                       text_color: str = "#FFFFFF", template_path: str = None,
                       width: int = 512, height: int = 512, 
                       text_position: str = "center") -> bytes:
    """Create a WebP sticker with custom settings"""
    try:
        # Create image with transparent background
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Load template if provided
        if template_path and os.path.exists(template_path):
            template = Image.open(template_path)
            template = template.convert('RGBA')
            template = template.resize((width, height), Image.Resampling.LANCZOS)
            img.paste(template, (0, 0), template)
        
        # Process Arabic/Persian text
        if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
            try:
                reshaped_text = arabic_reshaper.reshape(text)
                display_text = get_display(reshaped_text)
            except:
                display_text = text
        else:
            display_text = text
        
        # Load font with fallback
        font = None
        font_paths = [
            font_path,
            "fonts/Vazirmatn-Regular.ttf",
            "fonts/IRANSans.ttf",
            "fonts/Sahel.ttf",
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
        
        # Position text based on setting
        if text_position == "center":
            x = (width - text_width) // 2
            y = (height - text_height) // 2
        elif text_position == "top":
            x = (width - text_width) // 2
            y = 50
        elif text_position == "bottom":
            x = (width - text_width) // 2
            y = height - text_height - 50
        elif text_position == "left":
            x = 50
            y = (height - text_height) // 2
        elif text_position == "right":
            x = width - text_width - 50
            y = (height - text_height) // 2
        else:  # default center
            x = (width - text_width) // 2
            y = (height - text_height) // 2
        
        # Add shadow for better visibility
        shadow_offset = 2
        draw.text((x + shadow_offset, y + shadow_offset), display_text, font=font, fill="#000000")
        
        # Draw main text
        draw.text((x, y), display_text, font=font, fill=text_color)
        
        # Convert to RGB for WebP
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if needed
        if width > 512 or height > 512:
            img = img.resize((512, 512), Image.Resampling.LANCZOS)
        
        # Save as WebP
        output = io.BytesIO()
        img.save(output, format='WebP', quality=95, method=6, optimize=True)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating WebP sticker: {e}")
        return None

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Initialize user data
    if user_id not in USERS:
        USERS[user_id] = {
            "first_name": update.effective_user.first_name,
            "join_date": datetime.now(timezone.utc).isoformat()
        }
        save_users()
    
    welcome_text = (
        "🎨 به ربات استیکر ساز پیشرفته خوش آمدید!\n\n"
        "🔹 ساخت استیکر با متن دلخواه\n"
        "🔹 حالت ساده و پیشرفته\n"
        "🔹 مدیریت سهمیه روزانه\n"
        "🔹 پشتیبانی از زبان فارسی و انگلیسی"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_menu")],
        [InlineKeyboardButton("📋 سهمیه من", callback_data="my_quota")],
        [InlineKeyboardButton("📖 راهنما", callback_data="help_menu")],
        [InlineKeyboardButton("📞 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME[1:]}")]
    ]
    
    if user_id == ADMIN_ID:
        keyboard.insert(-1, [InlineKeyboardButton("⚙️ پنل ادمین", callback_data="admin_panel")])
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.callback_query.message.reply_text("❌ دسترسی غیر مجاز!")
        return
    
    total_users = len(USERS)
    active_limits = len([uid for uid, limits in USER_LIMITS.items() if limits.get("advanced_count_today", 0) > 0])
    
    admin_text = (
        "⚙️ **پنل مدیریت ادمین**\n\n"
        f"👥 تعداد کل کاربران: `{total_users}`\n"
        f"⚡ کاربران فعال امروز: `{active_limits}`\n"
        f"📊 محدودیت پیشرفته: `{ADVANCED_DAILY_LIMIT}` در روز\n\n"
        "🔧 **آمار سیستم:**\n"
        f"📁 فایل کاربران: `{len(USERS)}` کاربر\n"
        f"📁 فایل لیمیت‌ها: `{len(USER_LIMITS)}` کاربر\n\n"
        f"🕐 زمان آخرین آپدیت: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}` UTC"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔄 ریست لیمیت کاربر", callback_data="admin_reset_limits")],
        [InlineKeyboardButton("📊 مشاهده آمار", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ]
    
    await update.callback_query.message.reply_text(
        admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def my_quota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's quota"""
    user_id = update.effective_user.id
    reset_daily_limits(user_id)
    limits = get_user_limits(user_id)
    
    used = limits["advanced_count_today"]
    remaining = ADVANCED_DAILY_LIMIT - used
    
    quota_text = (
        "📋 **سهمیه شما**\n\n"
        "🎨 **استیکر ساده:**\n"
        "✅ نامحدود - بدون محدودیت استفاده\n\n"
        "⚡ **استیکر پیشرفته:**\n"
        f"📊 استفاده شده امروز: `{used}` از `{ADVANCED_DAILY_LIMIT}`\n"
        f"🎯 باقی مانده: `{remaining}` استیکر\n\n"
    )
    
    if remaining == 0:
        quota_text += (
            "⚠️ **سهمیه پیشرفته تمام شده!**\n"
            "🕐 سهمیه شما هر 24 ساعت یکبار ریست می‌شود\n"
            "📱 می‌توانید از استیکر ساده (نامحدود) استفاده کنید"
        )
    elif remaining <= 1:
        quota_text += (
            "⚠️ **هشدار سهمیه:**\n"
            f"🎯 فقط `{remaining}` استفاده پیشرفته باقی مانده\n"
            "🕐 فردا سهمیه شما تمدید می‌شود"
        )
    else:
        quota_text += (
            "✅ **وضعیت سهمیه عالی!**\n"
            f"🎯 می‌توانید `{remaining}` استیکر پیشرفته دیگر بسازید"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    await update.callback_query.message.reply_text(
        quota_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help menu"""
    help_text = (
        "📖 **راهنمای کامل ربات**\n\n"
        "🎨 **دکمه استیکر ساز:**\n"
        "• **ساده:** فقط متن و عکس - بدون محدودیت\n"
        "• **پیشرفته:** متن، عکس، رنگ، اندازه، موقعیت - 3 بار در روز\n\n"
        "📋 **سهمیه من:**\n"
        "• مشاهده سهمیه روزانه و باقی‌مانده\n"
        "• ریست خودکار هر 24 ساعت\n\n"
        "📞 **پشتیبانی:**\n"
        "• ارتباط با ادمین برای سوالات و مشکلات\n\n"
        "📖 **راهنما (اینجا):**\n"
        "• مشاهده تمام توضیحات و نحوه استفاده\n\n"
        "⚙️ **پنل ادمین (فقط ادمین):**\n"
        "• مدیریت کاربران و مشاهده آمار\n\n"
        "---\n"
        "💡 **نکات مهم:**\n"
        "• استیکرهای ساده نامحدود هستند\n"
        "• استیکرهای پیشرفته محدودیت روزانه دارند\n"
        "• از زبان فارسی و انگلیسی پشتیبانی می‌شود\n"
        "• تمام استیکرها در فرمت WebP ساخته می‌شوند\n\n"
        "🆘 برای کمک بیشتر به پشتیبانی پیام دهید"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    await update.callback_query.message.reply_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def sticker_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sticker creation menu"""
    user_id = update.effective_user.id
    reset_daily_limits(user_id)
    limits = get_user_limits(user_id)
    remaining = ADVANCED_DAILY_LIMIT - limits["advanced_count_today"]
    
    menu_text = (
        "🎨 **انتخاب نوع استیکر ساز:**\n\n"
        "🎨 **استیکر ساده:**\n"
        "✅ نامحدود - فقط متن + عکس\n"
        "⚡ سریع و آسان\n\n"
        "⚡ **استیکر پیشرفته:**\n"
        f"🎊 باقی‌مانده: `{remaining}` از `{ADVANCED_DAILY_LIMIT}`\n"
        "🎨 متن + عکس + رنگ + اندازه + موقعیت\n"
        "⚡ قابلیت‌های کامل سفارشی‌سازی"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎨 استیکر ساده", callback_data="simple_sticker")],
        [InlineKeyboardButton("⚡ استیکر پیشرفته", callback_data="advanced_sticker")]
    ]
    
    if remaining == 0:
        keyboard[1] = [InlineKeyboardButton("⚡ استیکر پیشرفته (سهمیه تمام شد)", callback_data="quota_exceeded")]
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
    
    await update.callback_query.message.reply_text(
        menu_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def simple_sticker_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle simple sticker mode"""
    user_id = update.effective_user.id
    
    # Set user mode
    if user_id not in USERS:
        USERS[user_id] = {"mode": "simple"}
    else:
        USERS[user_id]["mode"] = "simple"
    save_users()
    
    text = (
        "🎨 **حالت استیکر ساده فعال شد**\n\n"
        "📝 **لطفا مراحل زیر را دنبال کنید:**\n"
        "1️⃣ متن مورد نظر خود را ارسال کنید\n"
        "2️⃣ عکس دلخواه را ارسال کنید\n\n"
        "✨ **ویژگی‌ها:**\n"
        "• نامحدود - بدون محدودیت استفاده\n"
        "• متن فارسی و انگلیسی\n"
        "• فرمت WebP با کیفیت بالا\n\n"
        "🚀 شروع کنید: متن خود را بفرستید!"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    await update.callback_query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def advanced_sticker_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle advanced sticker mode"""
    user_id = update.effective_user.id
    
    if not can_use_advanced(user_id):
        await update.callback_query.message.reply_text(
            "⚠️ سهمیه استیکر پیشرفته شما تمام شده است!\n\n"
            f"🎊 محدودیت: {ADVANCED_DAILY_LIMIT} در 24 ساعت\n"
            "🕐 سهمیه فردا تمدید می‌شود\n\n"
            "💡 می‌توانید از استیکر ساده (نامحدود) استفاده کنید"
        )
        return
    
    # Set user mode
    if user_id not in USERS:
        USERS[user_id] = {"mode": "advanced", "sticker_data": {}}
    else:
        USERS[user_id]["mode"] = "advanced"
        USERS[user_id]["sticker_data"] = {}
    save_users()
    
    text = (
        "⚡ **حالت استیکر پیشرفته فعال شد**\n\n"
        "🎨 **تنظیمات استیکر:**\n\n"
        "📝 **مرحله 1:** متن خود را ارسال کنید\n\n"
        "✨ **ویژگی‌های پیشرفته:**\n"
        "• انتخاب رنگ متن\n"
        "• تنظیم اندازه فونت\n"
        "• تعیین موقعیت متن\n"
        "• انتخاب قالب پس‌زمینه\n\n"
        f"🎊 سهمیه شما: {ADVANCED_DAILY_LIMIT - get_user_limits(user_id)['advanced_count_today']} استفاده باقی‌مانده\n\n"
        "🚀 شروع کنید: متن خود را بفرستید!"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]]
    await update.callback_query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# Callback Query Handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    # Main menu callbacks
    if callback_data == "sticker_menu":
        await sticker_menu(update, context)
    elif callback_data == "my_quota":
        await my_quota(update, context)
    elif callback_data == "help_menu":
        await help_menu(update, context)
    elif callback_data == "admin_panel":
        await admin_panel(update, context)
    elif callback_data == "back_to_main":
        await start(update, context)
    
    # Sticker creation callbacks
    elif callback_data == "simple_sticker":
        await simple_sticker_mode(update, context)
    elif callback_data == "advanced_sticker":
        await advanced_sticker_mode(update, context)
    elif callback_data == "quota_exceeded":
        await query.message.reply_text(
            "⚠️ سهمیه استیکر پیشرفته شما تمام شده است!\n\n"
            f"🎊 محدودیت: {ADVANCED_DAILY_LIMIT} در 24 ساعت\n"
            "🕐 سهمیه فردا تمدید می‌شود\n\n"
            "💡 می‌توانید از استیکر ساده (نامحدود) استفاده کنید"
        )

# Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text and photo messages"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        USERS[user_id] = {"mode": None}
        save_users()
        await start(update, context)
        return
    
    mode = USERS[user_id].get("mode")
    
    if mode == "simple":
        if update.message.text and not update.message.photo:
            # Simple mode - just text
            text = update.message.text
            sticker_bytes = create_webp_sticker(text)
            
            if sticker_bytes:
                sticker_file = io.BytesIO(sticker_bytes)
                await update.message.reply_sticker(sticker=sticker_file)
                await update.message.reply_text("✅ استیکر ساده شما ساخته شد!")
            else:
                await update.message.reply_text("❌ خطا در ساخت استیکر. لطفا دوباره تلاش کنید.")
        
        elif update.message.photo:
            # Handle photo for simple mode
            await update.message.reply_text("📷 عکس دریافت شد! حالا متن خود را بفرستید:")
    
    elif mode == "advanced":
        # Handle advanced mode logic
        sticker_data = USERS[user_id].get("sticker_data", {})
        
        if not sticker_data.get("text"):
            if update.message.text:
                sticker_data["text"] = update.message.text
                USERS[user_id]["sticker_data"] = sticker_data
                save_users()
                
                # Show advanced options (color, size, position)
                await show_advanced_options(update, context)
        
        # Handle other advanced steps...

async def show_advanced_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show advanced sticker options"""
    keyboard = [
        [
            InlineKeyboardButton("⚪ سفید", callback_data="adv_color:#FFFFFF"),
            InlineKeyboardButton("⚫ مشکی", callback_data="adv_color:#000000"),
            InlineKeyboardButton("🔴 قرمز", callback_data="adv_color:#FF0000")
        ],
        [
            InlineKeyboardButton("🔵 آبی", callback_data="adv_color:#0000FF"),
            InlineKeyboardButton("🟢 سبز", callback_data="adv_color:#00FF00"),
            InlineKeyboardButton("🟡 زرد", callback_data="adv_color:#FFFF00")
        ],
        [
            InlineKeyboardButton("📏 اندازه فونت", callback_data="adv_size"),
            InlineKeyboardButton("📍 موقعیت متن", callback_data="adv_position")
        ],
        [
            InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
        ]
    ]
    
    await update.message.reply_text(
        "⚡ **تنظیمات پیشرفته استیکر:**\n\n"
        "🎨 رنگ متن را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# Bot setup
def setup_bot():
    """Setup the bot with all handlers"""
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN not found in environment variables")
        return None
    
    application = Application.builder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_menu))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    return application

# Flask routes for Vercel
@app.route('/')
def home():
    return "Advanced Telegram Sticker Bot is running!"

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Handle webhook requests from Telegram"""
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

# Global bot instance
bot = None

def main():
    """Main function to run the bot"""
    global bot
    
    # Load existing data
    load_data()
    
    # Setup bot
    bot_app = setup_bot()
    if not bot_app:
        logger.error("Failed to setup bot")
        return
    
    bot = type('Bot', (), {'application': bot_app})()
    
    # Set webhook for Vercel deployment
    bot_token = os.environ.get("BOT_TOKEN")
    webhook_url = os.environ.get("VERCEL_URL")
    
    if bot_token and webhook_url:
        full_webhook_url = f"https://{webhook_url}/api/webhook"
        logger.info(f"Setting webhook to: {full_webhook_url}")
        
        try:
            asyncio.run(bot_app.bot.set_webhook(full_webhook_url))
            logger.info("Webhook set successfully")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
    
    # Start Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
