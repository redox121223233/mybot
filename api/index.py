#!/usr/bin/env python3
"""
Enhanced Telegram Sticker Bot - Working Version
Supports pack creation, website integration, and channel subscription
"""

import os
import json
import logging
import asyncio
import tempfile
import io
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
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
ADMIN_ID = 6053579919
SUPPORT_USERNAME = "@onedaytoalive"
ADVANCED_DAILY_LIMIT = 3
REQUIRED_CHANNEL = "@redoxbot_sticker"  # Required channel

# Data Storage
USERS: Dict[int, Dict[str, Any]] = {}
USER_LIMITS: Dict[int, Dict[str, Any]] = {}
STICKER_PACKS: Dict[str, Dict[str, Any]] = {}

def load_data():
    """Load data from files"""
    global USERS, USER_LIMITS, STICKER_PACKS
    try:
        if os.path.exists("/tmp/users.json"):
            with open("/tmp/users.json", 'r', encoding='utf-8') as f:
                USERS = json.load(f)
        if os.path.exists("/tmp/limits.json"):
            with open("/tmp/limits.json", 'r', encoding='utf-8') as f:
                USER_LIMITS = json.load(f)
        if os.path.exists("/tmp/packs.json"):
            with open("/tmp/packs.json", 'r', encoding='utf-8') as f:
                STICKER_PACKS = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        pass

def save_data():
    """Save data to files"""
    try:
        with open("/tmp/users.json", 'w', encoding='utf-8') as f:
            json.dump(USERS, f, ensure_ascii=False, indent=2)
        with open("/tmp/limits.json", 'w', encoding='utf-8') as f:
            json.dump(USER_LIMITS, f, ensure_ascii=False, indent=2)
        with open("/tmp/packs.json", 'w', encoding='utf-8') as f:
            json.dump(STICKER_PACKS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        pass

async def check_channel_subscription(user_id: int, bot: Bot) -> bool:
    """Check if user is subscribed to required channel"""
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking channel subscription: {e}")
        return False  # Assume not subscribed if error occurs

def validate_pack_name(pack_name: str) -> tuple[bool, str]:
    """Validate sticker pack name according to Telegram rules"""
    if not pack_name or len(pack_name.strip()) == 0:
        return True, "no_pack"
    
    pack_name = pack_name.strip()
    
    # Length validation
    if len(pack_name) > 64:
        return False, "نام پک نباید بیشتر از ۶۴ کاراکتر باشد"
    
    # Character validation (Persian, English, numbers, underscore)
    if not re.match(r'^[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFFa-zA-Z0-9_]+$', pack_name):
        return False, "نام پک فقط می‌تواند شامل حروف فارسی، انگلیسی، عدد و خط زیر (_) باشد"
    
    # Check for existing packs
    if pack_name in STICKER_PACKS:
        return False, "این نام پک از قبل وجود دارد. لطفاً نام دیگری انتخاب کنید"
    
    # Check for inappropriate content
    forbidden_words = ['fuck', 'shit', 'admin', 'moderator', 'telegram', 'bot']
    for word in forbidden_words:
        if word.lower() in pack_name.lower():
            return False, "نام پک حاوی کلمات نامناسب است"
    
    return True, "valid"

def get_limits(user_id: int) -> Dict[str, Any]:
    """Get user limits"""
    if user_id not in USER_LIMITS:
        USER_LIMITS[user_id] = {
            "advanced_used": 0,
            "last_reset": datetime.now(timezone.utc).isoformat(),
            "total_stickers": 0
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
    limits["total_stickers"] += 1
    save_data()

def get_remaining(user_id: int) -> int:
    """Get remaining advanced stickers"""
    reset_daily_limit(user_id)
    return ADVANCED_DAILY_LIMIT - get_limits(user_id)["advanced_used"]

def create_sticker(text: str, image_data: Optional[bytes] = None, 
                   position: str = "center", font_size: int = 40, 
                   color: str = "#FFFFFF", background: Optional[str] = None) -> bytes:
    """Create sticker with advanced options"""
    try:
        # Create canvas
        canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        # Add background if specified
        if background:
            if background.startswith('gradient'):
                # Create gradient
                for y in range(512):
                    if background == 'gradient1':
                        r = int(102 + (153 * y / 512))
                        g = int(126 + (126 * y / 512))
                        b = int(234 + (18 * y / 512))
                    elif background == 'gradient2':
                        r = int(240 + (15 * y / 512))
                        g = int(147 + (40 * y / 512))
                        b = int(251 - (85 * y / 512))
                    elif background == 'gradient3':
                        r = int(245 + (10 * y / 512))
                        g = int(87 + (120 * y / 512))
                        b = int(108 + (148 * y / 512))
                    else:
                        r, g, b = 255, 255, 255
                    
                    for x in range(512):
                        canvas.putpixel((x, y), (r, g, b, 255))
            else:
                # Solid colors
                solid_colors = {
                    'solid1': (255, 255, 255, 255),  # White
                    'solid2': (0, 0, 0, 255),        # Black
                    'solid3': (70, 130, 255, 255)    # Blue
                }
                bg_color = solid_colors.get(background, (255, 255, 255, 255))
                canvas = Image.new('RGBA', (512, 512), bg_color)
        
        # Load and process image if provided
        if image_data:
            img = Image.open(io.BytesIO(image_data))
            img = img.convert('RGBA')
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
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
        
        # Calculate text position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position mapping
        positions = {
            "top-left": (100, 100),
            "top-center": (256, 100),
            "top-right": (412, 100),
            "center-left": (100, 256),
            "center": (256, 256),
            "center-right": (412, 256),
            "bottom-left": (100, 412),
            "bottom-center": (256, 412),
            "bottom-right": (412, 412)
        }
        
        x, y = positions.get(position, (256, 256))
        x = x - text_width // 2
        y = y - text_height // 2
        
        # Add shadow
        shadow_color = "#000000" if color != "#000000" else "#FFFFFF"
        draw.text((x + 2, y + 2), text, font=font, fill=shadow_color)
        
        # Draw main text
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
SESSIONS: Dict[int, Dict[str, Any]] = {}

def get_session(user_id: int) -> Dict[str, Any]:
    """Get user session"""
    if user_id not in SESSIONS:
        SESSIONS[user_id] = {}
    return SESSIONS[user_id]

def clear_session(user_id: int):
    """Clear user session"""
    if user_id in SESSIONS:
        del SESSIONS[user_id]

def get_main_menu(webapp_url: Optional[str] = None) -> list:
    """Get main menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🎨 استیکر ساز", callback_data="sticker_maker")],
        [InlineKeyboardButton("📊 سهمیه من", callback_data="quota")],
        [InlineKeyboardButton("📖 راهنما", callback_data="help")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")]
    ]
    
    if webapp_url:
        keyboard.insert(1, [InlineKeyboardButton("🌐 ساخت استیکر آنلاین", web_app=WebAppInfo(url=webapp_url))])
    
    return keyboard

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start"""
    user_id = update.effective_user.id
    
    # Check channel subscription
    is_subscribed = await check_channel_subscription(user_id, context.bot)
    if not is_subscribed:
        keyboard = [[InlineKeyboardButton("📺 عضویت در کانال", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")]]
        await update.message.reply_text(
            f"❌ **لطفاً ابتدا در کانال عضو شوید!**\n\n"
            f"📺 کانال: {REQUIRED_CHANNEL}\n"
            f"بعد از عضویت، دوباره /start را بزنید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    # Register user
    if user_id not in USERS:
        USERS[user_id] = {
            "first_name": update.effective_user.first_name,
            "username": update.effective_user.username,
            "joined_at": datetime.now(timezone.utc).isoformat()
        }
        save_data()
    
    # Get webapp URL
    webapp_url = os.environ.get("WEBAPP_URL", "https://mybot32.vercel.app")
    
    text = (
        f"🎨 به {BOT_USERNAME} خوش آمدید!\n\n"
        "✨ **ویژگی‌ها:**\n"
        "📍 **استیکر ساده:** نامحدود (عکس + متن)\n"
        "⚡ **استیکر پیشرفته:** ۳ بار در روز (عکس + متن + تنظیمات کامل)\n"
        "🌐 **سازنده آنلاین:** ساخت استیکر از وب‌سایت\n"
        "📦 **پک استیکر:** ایجاد پک شخصی\n\n"
        "📊 سهمیه شما در بخش «سهمیه من» قابل مشاهده است"
    )
    
    await update.message.reply_text(
        text, 
        reply_markup=InlineKeyboardMarkup(get_main_menu(webapp_url)),
        parse_mode='Markdown'
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ فقط ادمین!")
        return
    
    total_users = len(USERS)
    total_packs = len(STICKER_PACKS)
    total_stickers = sum(limit.get("total_stickers", 0) for limit in USER_LIMITS.values())
    
    text = (
        f"👹 **پنل ادمین {BOT_USERNAME}**\n\n"
        f"👥 **کاربران:** {total_users}\n"
        f"📦 **پک‌ها:** {total_packs}\n"
        f"🎨 **کل استیکرها:** {total_stickers}\n"
        f"⚡ **لیمیت روزانه:** {ADVANCED_DAILY_LIMIT}\n"
        f"📊 **وضعیت:** فعال ✅\n\n"
        f"🌐 **وب‌سایت:** {os.environ.get('WEBAPP_URL', 'https://mybot32.vercel.app')}"
    )
    
    await update.message.reply_text(
        text, 
        reply_markup=InlineKeyboardMarkup(get_main_menu()),
        parse_mode='Markdown'
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    text = (
        f"📖 **راهنمای {BOT_USERNAME}**\n\n"
        "🎨 **استیکر ساده:**\n"
        "• نامحدود استفاده\n"
        "• عکس + متن دلخواه\n"
        "• مناسب برای شروع\n\n"
        "⚡ **استیکر پیشرفته:**\n"
        f"• {ADVANCED_DAILY_LIMIT} بار در روز\n"
        "• تعیین موقعیت متن (۹ حالت)\n"
        "• تنظیم اندازه فونت (۲۰-۸۰ پیکسل)\n"
        "• انتخاب رنگ متن دلخواه\n"
        "• پس‌زمینه پیش‌فرض\n\n"
        "🌐 **سازنده آنلاین:**\n"
        "• ساخت استیکر از وب‌سایت\n"
        "• رابط کاربری حرفه‌ای\n"
        "• پیش‌نمایش زنده\n\n"
        "📦 **قوانین نام پک:**\n"
        "• حداکثر ۶۴ کاراکتر\n"
        "• فقط حروف فارسی/انگلیسی، عدد و _\n"
        "• نام پک باید منحصر به فرد باشد\n\n"
        "📞 **پشتیبانی:**\n"
        f"• ادمین: {SUPPORT_USERNAME}\n"
        f"• ربات: {BOT_USERNAME}\n\n"
        "📝 **نحوه استفاده:**\n"
        "۱. استیکر ساز → ساده یا پیشرفته\n"
        "۲. ارسال عکس (اختیاری برای ساده)\n"
        "۳. نوشتن متن\n"
        "۴. دریافت استیکر"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
    
    if update.message:
        await update.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.message.reply_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    webapp_url = os.environ.get("WEBAPP_URL", "https://mybot32.vercel.app")
    
    if data == "sticker_maker":
        keyboard = [
            [InlineKeyboardButton("🎨 استیکر ساده", callback_data="simple")],
            [InlineKeyboardButton("⚡ استیکر پیشرفته", callback_data="advanced")],
            [InlineKeyboardButton("🌐 سازنده آنلاین", web_app=WebAppInfo(url=webapp_url))],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        
        text = (
            f"🎨 **نوع استیکر {BOT_USERNAME} را انتخاب کنید:**\n\n"
            "📍 **ساده:** نامحدود استفاده\n"
            "   فقط عکس + متن\n\n"
            "⚡ **پیشرفته:** ۳ بار در روز\n"
            "   عکس + متن + تنظیمات کامل\n\n"
            "🌐 **آنلاین:** از طریق وب‌سایت\n"
            "   رابط کاربری حرفه‌ای"
        )
        
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "simple":
        session = get_session(user_id)
        session["mode"] = "simple"
        session["pack_name"] = None
        
        text = (
            "🎨 **استیکر ساده**\n\n"
            "📸 **مراحل:**\n"
            "۱. عکس خود را ارسال کنید (اختیاری)\n"
            "۲. متن خود را بنویسید\n"
            "۳. استیکر را دریافت کنید\n\n"
            "💡 *نکته:* می‌توانید فقط متن هم ارسال کنید"
        )
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif data == "advanced":
        if not can_use_advanced(user_id):
            remaining = get_remaining(user_id)
            await query.edit_message_text(
                f"⚠️ **سهمیه پیشرفته تمام شده!**\n\n"
                f"📊 استفاده شده: {ADVANCED_DAILY_LIMIT - remaining} از {ADVANCED_DAILY_LIMIT}\n"
                f"⏰ فردا سهمیه شما ریست می‌شود\n\n"
                f"💡 می‌توانید از استیکر ساده یا سازنده آنلاین استفاده کنید"
            )
            return
        
        session = get_session(user_id)
        session["mode"] = "advanced"
        session["settings"] = {
            "position": "center",
            "font_size": 40,
            "color": "#FFFFFF",
            "background": None
        }
        
        remaining = get_remaining(user_id)
        
        keyboard = [
            [InlineKeyboardButton("📍 موقعیت متن", callback_data="adv_position")],
            [InlineKeyboardButton("📏 اندازه فونت", callback_data="adv_size")],
            [InlineKeyboardButton("🎨 رنگ متن", callback_data="adv_color")],
            [InlineKeyboardButton("🖼️ پس‌زمینه", callback_data="adv_background")],
            [InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
        ]
        
        text = (
            f"⚡ **استیکر پیشرفته**\n\n"
            f"📊 **سهمیه:** {remaining} از {ADVANCED_DAILY_LIMIT}\n\n"
            "⚙️ **تنظیمات خود را انتخاب کنید:**"
        )
        
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "adv_position":
        session = get_session(user_id)
        keyboard = [
            [InlineKeyboardButton("↖️", callback_data="pos_top-left"), 
             InlineKeyboardButton("⬆️", callback_data="pos_top-center"), 
             InlineKeyboardButton("↗️", callback_data="pos_top-right")],
            [InlineKeyboardButton("⬅️", callback_data="pos_center-left"), 
             InlineKeyboardButton("⭕", callback_data="pos_center"), 
             InlineKeyboardButton("➡️", callback_data="pos_center-right")],
            [InlineKeyboardButton("↙️", callback_data="pos_bottom-left"), 
             InlineKeyboardButton("⬇️", callback_data="pos_bottom-center"), 
             InlineKeyboardButton("↘️", callback_data="pos_bottom-right")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="advanced")]
        ]
        
        current_pos = session.get("settings", {}).get("position", "center")
        text = f"📍 **موقعیت متن:**当前位置 {current_pos}\n\nموقعیت جدید را انتخاب کنید:"
        
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith("pos_"):
        position = data.replace("pos_", "")
        session = get_session(user_id)
        session["settings"]["position"] = position
        
        await query.answer(f"موقعیت به {position} تغییر یافت")
        # Return to advanced menu
await button_callback(update, context)
    
    elif data == "adv_size":
        session = get_session(user_id)
        current_size = session.get("settings", {}).get("font_size", 40)
        
        text = f"📏 **اندازه فونت فعلی:** {current_size} پیکسل\n\nلطفاً اندازه جدید را بنویسید (۲۰-۸۰):"
        
        await query.edit_message_text(text, parse_mode='Markdown')
        session["waiting_font_size"] = True
    
    elif data == "adv_color":
        colors = [
            ("#FFFFFF", "سفید"), ("#000000", "مشکی"), ("#FF0000", "قرمز"),
            ("#00FF00", "سبز"), ("#0000FF", "آبی"), ("#FFFF00", "زرد"),
            ("#FF00FF", "مژانتی"), ("#00FFFF", "فیروزه‌ای"), ("#FFA500", "نارنجی")
        ]
        
        keyboard = []
        for i in range(0, len(colors), 3):
            row = []
            for color, name in colors[i:i+3]:
                row.append(InlineKeyboardButton(name, callback_data=f"color_{color}"))
            if row:
                keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="advanced")])
        
        text = "🎨 **رنگ متن را انتخاب کنید:**"
        
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith("color_"):
        color = data.replace("color_", "")
        session = get_session(user_id)
        session["settings"]["color"] = color
        
        await query.answer(f"رنگ به {color} تغییر یافت")
        await button_callback(update, context)
    
    elif data == "adv_background":
        backgrounds = [
            ("gradient1", "گرادیان آبی"), ("gradient2", "گرادیان بنفش"), ("gradient3", "گرادیان صورتی"),
            ("solid1", "سفید"), ("solid2", "مشکی"), ("solid3", "آبی"), ("none", "بدون پس‌زمینه")
        ]
        
        keyboard = []
        for i in range(0, len(backgrounds), 2):
            row = []
            for bg, name in backgrounds[i:i+2]:
                row.append(InlineKeyboardButton(name, callback_data=f"bg_{bg}"))
            if row:
                keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="advanced")])
        
        text = "🖼️ **پس‌زمینه را انتخاب کنید:**"
        
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith("bg_"):
        bg = data.replace("bg_", "")
        session = get_session(user_id)
        session["settings"]["background"] = None if bg == "none" else bg
        
        await query.answer(f"پس‌زمینه به {bg} تغییر یافت")
        await button_callback(update, context)
    
    elif data == "adv_create":
        session = get_session(user_id)
        session["waiting_image"] = True
        
        text = (
            "✅ **آماده ساخت استیکر پیشرفته**\n\n"
            "📸 **مراحل:**\n"
            "۱. عکس خود را ارسال کنید (اختیاری)\n"
            "۲. متن خود را بنویسید\n"
            "۳. استیکر با تنظیمات شما ساخته می‌شود\n\n"
            "⚙️ **تنظیمات فع:**\n"
            f"📍 موقعیت: {session['settings']['position']}\n"
            f"📏 اندازه: {session['settings']['font_size']}px\n"
            f"🎨 رنگ: {session['settings']['color']}\n"
            f"🖼️ پس‌زمینه: {session['settings']['background'] or 'ندارد'}"
        )
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif data == "quota":
        reset_daily_limit(user_id)
        remaining = get_remaining(user_id)
        used = ADVANCED_DAILY_LIMIT - remaining
        limits = get_limits(user_id)
        total_stickers = limits.get("total_stickers", 0)
        
        # Calculate time until reset
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
            f"📊 **سهمیه شما در {BOT_USERNAME}**\n\n"
            f"🎨 **استیکر ساده:**\n"
            f"✅ نامحدود استفاده\n\n"
            f"⚡ **استیکر پیشرفته:**\n"
            f"📈 استفاده شده: {used} از {ADVANCED_DAILY_LIMIT}\n"
            f"📊 باقی‌مانده: {remaining} استیکر\n"
            f"🎯 کل استیکرها: {total_stickers}\n"
            f"{time_text}\n\n"
            f"🌐 **سازنده آنلاین:**\n"
            f"✅ همیشه در دسترس\n"
            f"🔗 {webapp_url}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "help":
        await help_cmd(update, context)
    
    elif data == "support":
        text = (
            f"📞 **پشتیبانی {BOT_USERNAME}**\n\n"
            f"👨‍💻 **ادمین:** {SUPPORT_USERNAME}\n"
            f"🤖 **ربات:** {BOT_USERNAME}\n\n"
            "📍 **برای سوال و مشکل:**\n"
            "• با ادمین در ارتباط باشید\n"
            "• از طریق تلگرام پیام دهید\n\n"
            f"💬 [{SUPPORT_USERNAME}](https://t.me/{SUPPORT_USERNAME[1:]})"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back")]]
        await query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "back":
        webapp_url = os.environ.get("WEBAPP_URL", "https://mybot32.vercel.app")
        await query.edit_message_text(
            f"🎨 به {BOT_USERNAME} خوش آمدید!\n\nیک گزینه را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(get_main_menu(webapp_url))
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo upload"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    if "mode" not in session and not session.get("waiting_image"):
        return
    
    try:
        photo_file = await update.message.photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        session["image"] = photo_bytes
        session["waiting_text"] = True
        
        if session.get("waiting_image"):
            await update.message.reply_text("✅ عکس دریافت شد!\n\n📝 متن خود را بنویسید:")
            session["waiting_image"] = False
        else:
            await update.message.reply_text("✅ عکس دریافت شد!\n\n📝 متن خود را بنویسید:")
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await update.message.reply_text("❌ خطا در دریافت عکس")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input"""
    user_id = update.effective_user.id
    session = get_session(user_id)
    
    # Handle font size input for advanced mode
    if session.get("waiting_font_size"):
        try:
            font_size = int(update.message.text)
            if 20 <= font_size <= 80:
                session["settings"]["font_size"] = font_size
                session["waiting_font_size"] = False
                
                await update.message.reply_text(
                    f"✅ اندازه فونت به {font_size} پیکسل تغییر یافت",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data="advanced")
                    ]])
                )
                
                # Return to advanced menu
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚡ **استیکر پیشرفته**\n\n⚙️ **تنظیمات خود را انتخاب کنید:**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📍 موقعیت متن", callback_data="adv_position")],
                        [InlineKeyboardButton("📏 اندازه فونت", callback_data="adv_size")],
                        [InlineKeyboardButton("🎨 رنگ متن", callback_data="adv_color")],
                        [InlineKeyboardButton("🖼️ پس‌زمینه", callback_data="adv_background")],
                        [InlineKeyboardButton("✅ ساخت استیکر", callback_data="adv_create")],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data="back")]
                    ]),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ اندازه باید بین ۲۰ تا ۸۰ باشد!")
        except ValueError:
            await update.message.reply_text("❌ لطفاً فقط عدد وارد کنید!")
        return
    
    if not session.get("waiting_text"):
        return
    
    text = update.message.text
    image_data = session.get("image")
    mode = session.get("mode")
    
    if not mode:
        return
    
    await update.message.reply_text("⏳ در حال ساخت استیکر...")
    
    try:
        if mode == "simple":
            # Simple sticker
            sticker_bytes = create_sticker(text, image_data)
        elif mode == "advanced":
            # Advanced sticker with custom settings
            settings = session.get("settings", {})
            sticker_bytes = create_sticker(
                text, image_data,
                position=settings.get("position", "center"),
                font_size=settings.get("font_size", 40),
                color=settings.get("color", "#FFFFFF"),
                background=settings.get("background")
            )
            use_advanced(user_id)
        
        if sticker_bytes:
            sticker_file = io.BytesIO(sticker_bytes)
            sticker_file.name = f"sticker_{hash(text + str(datetime.now()))}.webp"
            
            await update.message.reply_sticker(sticker=sticker_file)
            
            if mode == "advanced":
                remaining = get_remaining(user_id)
                webapp_url = os.environ.get("WEBAPP_URL", "https://mybot32.vercel.app")
                
                await update.message.reply_text(
                    f"✅ **استیکر پیشرفته ساخته شد!** 🎉\n\n"
                    f"📊 سهمیه باقی‌مانده: {remaining} از {ADVANCED_DAILY_LIMIT}\n\n"
                    f"🌐 **برای استیکرهای بیشتر:**\n"
                    f"💻 استفاده از وب‌سایت: {webapp_url}\n"
                    f"📱 یا فردا مراجعه کنید",
                    reply_markup=InlineKeyboardMarkup(get_main_menu(webapp_url)),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "✅ **استیکر ساده ساخته شد!** 🎉\n\n"
                    "🎨 برای استیکر جدید از منو استفاده کنید\n"
                    "💡 یا از سازنده آنلاین استفاده کنید",
                    reply_markup=InlineKeyboardMarkup(get_main_menu()),
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text("❌ خطا در ساخت استیکر")
        
        clear_session(user_id)
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        await update.message.reply_text("❌ خطا در ساخت استیکر")
        clear_session(user_id)

# Flask routes
@app.route('/')
def home():
    """Home page redirect"""
    return "Enhanced Sticker Bot is running!"

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Webhook handler for Telegram bot"""
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

@app.route('/api/webhook', methods=['GET'])
def webhook_status():
    """Webhook status check"""
    return "Enhanced Bot API is running", 200

@app.route('/api/create-sticker', methods=['POST'])
def create_sticker_api():
    """API for website sticker creation"""
    try:
        data = request.get_json()
        
        # Extract data
        text = data.get('text', '')
        pack_name = data.get('pack_name', '')
        mode = data.get('mode', 'simple')
        position = data.get('position', 'center')
        font_size = int(data.get('font_size', 40))
        color = data.get('color', '#FFFFFF')
        background = data.get('background')
        
        # Handle image data
        image_data = None
        if 'image' in data and data['image']:
            import base64
            image_data = base64.b64decode(data['image'].split(',')[1])
        
        # Validate pack name
        if pack_name:
            is_valid, message = validate_pack_name(pack_name)
            if not is_valid:
                return jsonify({'error': message}), 400
        
        # Create sticker
        sticker_bytes = create_sticker(
            text, image_data, position, font_size, color, background
        )
        
        if sticker_bytes:
            # Convert to base64 for response
            import base64
            sticker_base64 = base64.b64encode(sticker_bytes).decode('utf-8')
            
            response = {
                'success': True,
                'sticker': f'data:image/webp;base64,{sticker_base64}',
                'message': 'استیکر با موفقیت ساخته شد!'
            }
            
            return jsonify(response)
        else:
            return jsonify({'error': 'خطا در ساخت استیکر'}), 500
            
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'error': 'خطای سرور'}), 500

@app.route('/api/check-quota', methods=['GET'])
def check_quota_api():
    """Check user quota"""
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        reset_daily_limit(user_id)
        remaining = get_remaining(user_id)
        
        return jsonify({
            'remaining': remaining,
            'total': ADVANCED_DAILY_LIMIT,
            'used': ADVANCED_DAILY_LIMIT - remaining
        })
        
    except Exception as e:
        logger.error(f"Quota check error: {e}")
        return jsonify({'error': 'خطا در بررسی سهمیه'}), 500

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
    logger.info(f"Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()