#!/usr/bin/env python3
"""
Complete integrated Telegram Bot for Vercel
Perfect Sticker Bot without webp format issues
"""

import os
import json
import logging
import asyncio
import random
import tempfile
import io
import base64
from datetime import datetime, timezone
import secrets
import uuid
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InputSticker
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
CHANNEL_USERNAME = "@redoxbot_sticker"

# Data Persistence (File-based)
USERS: dict[int, dict] = {}
SESSIONS: dict[int, dict] = {}
USER_FILE = "/tmp/users.json"
SESSION_FILE = "/tmp/sessions.json"

def load_data():
    """Load user and session data from files"""
    global USERS, SESSIONS
    try:
        if os.path.exists(USER_FILE):
            with open(USER_FILE, 'r') as f:
                USERS = json.load(f)
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                SESSIONS = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")

def save_users():
    """Save the USERS dictionary to a file"""
    try:
        with open(USER_FILE, 'w') as f:
            json.dump(USERS, f)
    except Exception as e:
        logger.error(f"Failed to save users: {e}")

def save_sessions():
    """Save the SESSIONS dictionary to a file"""
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(SESSIONS, f)
    except Exception as e:
        logger.error(f"Failed to save sessions: {e}")

def user(uid: int) -> dict:
    """Get or create user data"""
    if uid not in USERS:
        USERS[uid] = {
            "first_name": "",
            "ai_used": 0,
            "sticker_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    return USERS[uid]

def sess(uid: int) -> dict:
    """Get or create session data"""
    if uid not in SESSIONS:
        SESSIONS[uid] = {"mode": "main", "sticker_data": {}, "pending_stickers": {}}
    return SESSIONS[uid]

def reset_mode(uid: int):
    """Reset user mode while optionally preserving pack state"""
    current_sess = sess(uid)
    
    # Preserve pack-specific data if in sticker creation flow
    pack_data = {}
    if "current_pack_name" in current_sess:
        pack_data["current_pack_name"] = current_sess["current_pack_name"]
    if "current_pack_short_name" in current_sess:
        pack_data["current_pack_short_name"] = current_sess["current_pack_short_name"]
    
    # Reset session but keep pack data
    SESSIONS[uid] = {"mode": "main", "sticker_data": {}, "pending_stickers": {}, **pack_data}
    save_sessions()

def cleanup_pending_sticker(uid: int, lookup_key: str):
    """Clean up a specific pending sticker after processing"""
    try:
        if uid in SESSIONS:
            current_sess = SESSIONS[uid]
            pending_stickers = current_sess.get('pending_stickers', {})
            if lookup_key in pending_stickers:
                del pending_stickers[lookup_key]
                logger.info(f"Cleaned up pending sticker {lookup_key} for user {uid}")
                save_sessions()
    except Exception as e:
        logger.error(f"Error cleaning up pending sticker {lookup_key} for user {uid}: {e}")

def get_current_pack_name(user_id: int) -> str:
    """Get the current sticker pack name for user"""
    current_sess = sess(user_id)
    return current_sess.get("current_pack_name", "")

def get_current_pack_short_name(user_id: int) -> str:
    """Get the current sticker pack short name for user"""
    current_sess = sess(user_id)
    return current_sess.get("current_pack_short_name", "")

def check_pack_exists(pack_short_name: str) -> bool:
    """Check if a sticker pack exists using direct API"""
    try:
        from telegram import Bot
        bot_token = os.environ.get("BOT_TOKEN")
        if not bot_token:
            return False
            
        bot = Bot(token=bot_token)
        result = asyncio.run(bot.get_sticker_set(pack_short_name))
        
        if result and hasattr(result, 'stickers'):
            stickers = result.stickers
            logger.info(f"✅ Pack {pack_short_name} exists with {len(stickers)} stickers (direct API)")
            return True
        else:
            return False
            
    except Exception as e:
        error_desc = str(e).lower()
        if "stickerset_invalid" in error_desc or "not found" in error_desc:
            logger.info(f"❌ Pack {pack_short_name} does not exist")
            return False
        else:
            logger.warning(f"Error checking pack {pack_short_name}: {e}")
            return False

def get_pack_status(pack_short_name: str) -> dict:
    """Get detailed status of a sticker pack using direct API"""
    try:
        from telegram import Bot
        bot_token = os.environ.get("BOT_TOKEN")
        if not bot_token:
            return {"exists": False}
            
        bot = Bot(token=bot_token)
        result = asyncio.run(bot.get_sticker_set(pack_short_name))
        
        if result and hasattr(result, 'stickers'):
            stickers = result.stickers
            return {
                "exists": True,
                "count": len(stickers),
                "is_full": len(stickers) >= 120
            }
        else:
            return {"exists": False}
            
    except Exception as e:
        error_desc = str(e).lower()
        if "stickerset_invalid" in error_desc or "not found" in error_desc:
            return {"exists": False}
        else:
            logger.warning(f"Error getting pack status {pack_short_name}: {e}")
            return {"exists": False, "error": str(e)}

def create_webp_sticker(text: str, font_path: str = None, font_size: int = 40, 
                       text_color: str = "#FFFFFF", template_path: str = None,
                       width: int = 512, height: int = 512) -> bytes:
    """Create a perfect WebP sticker with proper format handling"""
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
        
        # Position text in center
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Add shadow for better visibility
        shadow_offset = 2
        draw.text((x + shadow_offset, y + shadow_offset), display_text, font=font, fill="#000000")
        
        # Draw main text
        draw.text((x, y), display_text, font=font, fill=text_color)
        
        # Convert to RGB for WebP compatibility
        if img.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Special settings for Telegram sticker packs
        if width > 512 or height > 512:
            img = img.resize((512, 512), Image.Resampling.LANCZOS)
        
        # Save as WebP with optimal settings
        output = io.BytesIO()
        img.save(output, format='WebP', quality=95, method=6, optimize=True)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating WebP sticker: {e}")
        # Create a simple fallback sticker
        try:
            fallback_img = Image.new('RGB', (512, 512), '#FF6B6B')
            fallback_draw = ImageDraw.Draw(fallback_img)
            fallback_font = ImageFont.load_default()
            fallback_draw.text((50, 256), text[:20], font=fallback_font, fill='#FFFFFF')
            
            output = io.BytesIO()
            fallback_img.save(output, format='WebP', quality=90)
            output.seek(0)
            return output.getvalue()
        except:
            return None

async def sticker_confirm_logic(message, context):
    """Enhanced sticker creation logic with perfect webp handling"""
    try:
        user_id = message.from_user.id
        current_sess = sess(user_id)
        sticker_data = current_sess.get("sticker_data", {})
        
        # Extract sticker data
        text = sticker_data.get("text", "")
        template = sticker_data.get("template", None)
        font = sticker_data.get("font", "fonts/Vazirmatn-Regular.ttf")
        size = sticker_data.get("size", 40)
        color = sticker_data.get("color", "#FFFFFF")
        
        # Create sticker with perfect WebP handling
        logger.info(f"Creating sticker for user {user_id} with text: {text}")
        
        template_path = None
        if template:
            template_path = f"templates/{template}"
            if not os.path.exists(template_path):
                logger.warning(f"Template {template_path} not found")
                template_path = None
        
        sticker_bytes = create_webp_sticker(
            text=text,
            font_path=font,
            font_size=size,
            text_color=color,
            template_path=template_path,
            width=512,
            height=512
        )
        
        if not sticker_bytes:
            raise Exception("Failed to create sticker image")
        
        # Upload sticker file with proper handling
        sticker_file = io.BytesIO(sticker_bytes)
        sticker_file.name = f"sticker_{uuid.uuid4().hex[:8]}.webp"
        
        # Send sticker to user
        await message.reply_sticker(sticker=sticker_file)
        
        # Save sticker file for pack operations
        sent_message = await message.reply_sticker(sticker=sticker_file)
        if sent_message.sticker:
            file_id = sent_message.sticker.file_id
            
            # Store for pack operations
            lookup_key = f"{user_id}_{uuid.uuid4().hex[:8]}"
            pending_stickers = current_sess.get('pending_stickers', {})
            pending_stickers[lookup_key] = file_id
            current_sess['pending_stickers'] = pending_stickers
            save_sessions()
            
            # Track AI usage if applicable
            if current_sess.get("sticker_mode") == "advanced" and user_id != ADMIN_ID:
                u = user(user_id)
                u["ai_used"] = u.get("ai_used", 0) + 1
                save_users()

            keyboard = [[InlineKeyboardButton("✅ افزودن به پک", callback_data=f"add_sticker:{lookup_key}")]]
            await message.reply_text(
                "✅ استیکر شما با موفقیت ساخته و آپلود شد!\n\n"
                "برای اضافه کردن نهایی به پک، دکمه زیر را فشار دهید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except Exception as e:
        logger.error(f"STAGE 1 FAILED for user {user_id}: {e}", exc_info=True)
        await message.reply_text(f"خطا در مرحله اول ساخت استیکر: {e}")

async def add_sticker_to_pack_improved(context, user_id, pack_short_name, sticker_file_id):
    """Improved sticker addition with retry logic and webp format support"""
    try:
        max_attempts = 3
        success = False
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_attempts} to add sticker to pack...")
                
                # Add delay between attempts to avoid rate limiting
                if attempt > 0:
                    await asyncio.sleep(2 ** attempt)  # 2s, 4s delay
                
                from telegram import InputSticker
                
                await context.bot.add_sticker_to_set(
                    user_id=user_id, 
                    name=pack_short_name, 
                    sticker=InputSticker(
                        sticker=sticker_file_id,
                        emoji_list=["😊"]
                    )
                )
                
                logger.info(f"✅ SUCCESS: Sticker added to pack {pack_short_name} on attempt {attempt + 1}")
                success = True
                break
                
            except BadRequest as e:
                attempt_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed: {attempt_error}")
                
                if "PACK_TOO_SHORT" in attempt_error:
                    logger.error(f"Pack name validation failed: {attempt_error}")
                    break
                elif "STICKERS_TOO_MUCH" in attempt_error:
                    logger.error(f"Pack is full: {attempt_error}")
                    break
                elif "STICKER_DOCUMENT_INVALID" in attempt_error:
                    logger.error(f"Sticker format invalid: {attempt_error}")
                    break
                
                if attempt < max_attempts - 1:
                    continue
                else:
                    # All attempts failed, provide manual instructions
                    pack_link = f"https://t.me/addstickers/{pack_short_name}"
                    return {"success": False, "error": attempt_error, "manual_link": pack_link}
            
            except Exception as e:
                attempt_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed: {attempt_error}")
                
                if attempt < max_attempts - 1:
                    continue
                else:
                    # All attempts failed, provide manual instructions
                    pack_link = f"https://t.me/addstickers/{pack_short_name}"
                    return {"success": False, "error": attempt_error, "manual_link": pack_link}
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error in add_sticker_to_pack_improved: {e}")
        pack_link = f"https://t.me/addstickers/{pack_short_name}"
        return {"success": False, "error": str(e), "manual_link": pack_link}

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    reset_mode(user_id)
    
    welcome_text = (
        "🎨 به ربات ساز استیکر خوش آمدید!\n\n"
        "🔹 متن خود را بنویسید تا استیکر بسازیم\n"
        "🔹 از دستور /newpack برای ساخت پک جدید استفاده کنید\n"
        "🔹 از دستور /addtopack برای اضافه کردن به پک موجود استفاده کنید\n\n"
        "⚡ شروع کنید: متن مورد نظر خود را ارسال کنید"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎨 ساخت استیکر جدید", callback_data="create_sticker")],
        [InlineKeyboardButton("📦 ساخت پک جدید", callback_data="create_pack")],
        [InlineKeyboardButton("➕ اضافه به پک موجود", callback_data="add_to_pack")],
        [InlineKeyboardButton("📞 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME[1:]}")]
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def new_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newpack command"""
    user_id = update.effective_user.id
    current_sess = sess(user_id)
    
    # Reset and set mode for new pack creation
    reset_mode(user_id)
    current_sess["mode"] = "new_pack"
    save_sessions()
    
    await update.message.reply_text(
        "📦 برای ساخت پک استیکر جدید:\n\n"
        "1️⃣ نام پک را ارسال کنید (مثلا: استیکرهای من)\n"
        "2️⃣ نام کوتاه پک را ارسال کنید (مثلا: mystickers_by_bot)\n\n"
        "⚠️ نام کوتاه باید به انگلیسی و بدون فاصله باشد"
    )

async def add_to_pack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addtopack command"""
    user_id = update.effective_user.id
    current_sess = sess(user_id)
    
    # Set mode for adding to existing pack
    current_sess["mode"] = "add_to_pack"
    save_sessions()
    
    pack_short_name = get_current_pack_short_name(user_id)
    
    if pack_short_name:
        pack_link = f"https://t.me/addstickers/{pack_short_name}"
        await update.message.reply_text(
            f"📦 پک فعلی شما: {pack_short_name}\n"
            f"لینک پک: {pack_link}\n\n"
            "اگر می‌خواهید به پک دیگری اضافه کنید، نام کوتاه پک جدید را ارسال کنید.\n"
            "در غیر این صورت، متن استیکر خود را ارسال کنید."
        )
    else:
        await update.message.reply_text(
            "📦 برای اضافه کردن به پک موجود:\n\n"
            "نام کوتاه پک را ارسال کنید (مثلا: mystickers_by_bot)\n"
            "یا از /start برای ساخت پک جدید استفاده کنید"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "🤖 راهنمای ربات ساز استیکر:\n\n"
        "📝 دستورات اصلی:\n"
        "/start - شروع و منوی اصلی\n"
        "/newpack - ساخت پک استیکر جدید\n"
        "/addtopack - اضافه کردن به پک موجود\n"
        "/help - نمایش این راهنما\n\n"
        "🎨 نحوه استفاده:\n"
        "1. از /start شروع کنید\n"
        "2. ساخت استیکر جدید یا پک را انتخاب کنید\n"
        "3. متن خود را ارسال کنید\n"
        "4. استیکر ساخته شده را به پک اضافه کنید\n\n"
        "⚡ نکات مهم:\n"
        "• هر پک می‌تواند حداکثر 120 استیکر داشته باشد\n"
        "• استیکرها در فرمت WebP ساخته می‌شوند\n"
        "• از فونت‌های فارسی و انگلیسی پشتیبانی می‌شود\n\n"
        "📞 برای پشتیبانی: @onedaytoalive"
    )
    
    await update.message.reply_text(help_text)

# Message Handlers
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for sticker creation"""
    user_id = update.effective_user.id
    current_sess = sess(user_id)
    mode = current_sess.get("mode", "main")
    text = update.message.text
    
    logger.info(f"User {user_id} sent text in mode: {mode}")
    
    if mode == "new_pack":
        # Handle pack creation
        if "pack_name" not in current_sess:
            current_sess["pack_name"] = text
            save_sessions()
            await update.message.reply_text(
                "✅ نام پک ثبت شد.\n\n"
                "حالا نام کوتاه پک را به انگلیسی ارسال کنید:\n"
                "(مثلا: mystickers_by_bot)"
            )
        elif "pack_short_name" not in current_sess:
            pack_short_name = text.lower().replace(" ", "_").replace("-", "_")
            current_sess["pack_short_name"] = pack_short_name
            save_sessions()
            
            # Check if pack already exists
            if check_pack_exists(pack_short_name):
                await update.message.reply_text(
                    "⚠️ این پک قبلا ساخته شده است!\n"
                    "لطفا نام کوتاه دیگری انتخاب کنید."
                )
                del current_sess["pack_short_name"]
                save_sessions()
            else:
                await update.message.reply_text(
                    f"✅ نام کوتاه پک: {pack_short_name}\n\n"
                    "حالا متن اولین استیکر خود را ارسال کنید:"
                )
                current_sess["mode"] = "creating_sticker"
                save_sessions()
        else:
            # This shouldn't happen, but handle it
            await handle_sticker_text(update, context, text)
    
    elif mode == "add_to_pack":
        # Check if this is a pack name or sticker text
        if not get_current_pack_short_name(user_id):
            # This might be a pack short name
            potential_pack_name = text.lower().replace(" ", "_").replace("-", "_")
            if check_pack_exists(potential_pack_name):
                current_sess["current_pack_short_name"] = potential_pack_name
                save_sessions()
                await update.message.reply_text(
                    f"✅ پک انتخاب شد: {potential_pack_name}\n\n"
                    "حالا متن استیکر خود را ارسال کنید:"
                )
                current_sess["mode"] = "creating_sticker"
                save_sessions()
            else:
                await update.message.reply_text(
                    "⚠️ پکی با این نام پیدا نشد!\n"
                    "لطفا نام کوتاه صحیح پک را وارد کنید."
                )
        else:
            # This is sticker text
            await handle_sticker_text(update, context, text)
    
    elif mode == "main" or mode == "creating_sticker":
        # Direct sticker creation
        await handle_sticker_text(update, context, text)

async def handle_sticker_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle sticker text creation"""
    user_id = update.effective_user.id
    current_sess = sess(user_id)
    
    # Store sticker data
    current_sess["sticker_data"] = {
        "text": text,
        "template": None,
        "font": "fonts/Vazirmatn-Regular.ttf",
        "size": 40,
        "color": "#FFFFFF"
    }
    current_sess["mode"] = "main"
    save_sessions()
    
    # Create the sticker
    await sticker_confirm_logic(update.message, context)

# Callback Query Handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "create_sticker":
        reset_mode(user_id)
        await query.message.reply_text(
            "🎨 متن استیکر خود را ارسال کنید:\n\n"
            "میتوانید از فارسی و انگلیسی استفاده کنید"
        )
    
    elif callback_data == "create_pack":
        await new_pack(update, context)
    
    elif callback_data == "add_to_pack":
        await add_to_pack(update, context)
    
    elif callback_data.startswith("add_sticker:"):
        # --- Add sticker to pack logic ---
        await query.edit_message_text("⏳ در حال ارسال استیکر نهایی...", reply_markup=None)
        
        lookup_key = callback_data.split(":")[-1]
        current_sess = sess(user_id)
        
        pending_stickers = current_sess.get('pending_stickers', {})
        file_id = pending_stickers.get(lookup_key)
        
        if not file_id:
            await query.message.reply_text("❌ استیکر پیدا نشد. لطفا دوباره تلاش کنید.")
            cleanup_pending_sticker(user_id, lookup_key)
            return
        
        pack_short_name = get_current_pack_short_name(user_id)
        logger.info(f"📍 Current pack detected: {pack_short_name} for user {user_id}")
        
        # Try to add sticker with enhanced logic
        success = False
        for attempt in range(3):
            try:
                logger.info(f"Attempt {attempt + 1}/3 to add sticker to pack...")
                
                # Add delay between attempts
                if attempt > 0:
                    await asyncio.sleep(2 ** attempt)
                
                result = await add_sticker_to_pack_improved(context, user_id, pack_short_name, file_id)
                
                if result["success"]:
                    success = True
                    break
                elif "manual_link" in result:
                    # All attempts failed, provide manual instructions
                    pack_link = result["manual_link"]
                    await query.message.reply_text(
                        f"⚠️ افزودن خودکار انجام نشد. لطفا دستی اضافه کنید:\n\n"
                        f"1. روی استیکر کلیک کنید\n"
                        f"2. «Add to Pack» را انتخاب کنید\n\n"
                        f"لینک: {pack_link}"
                    )
                    break
            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    continue
                else:
                    # Final attempt failed
                    pack_link = f"https://t.me/addstickers/{pack_short_name}"
                    await query.message.reply_text(
                        f"⚠️ افزودن خودکار انجام نشد. لطفا دستی اضافه کنید:\n\n"
                        f"1. روی استیکر کلیک کنید\n"
                        f"2. «Add to Pack» را انتخاب کنید\n\n"
                        f"لینک: {pack_link}"
                    )
        
        if success:
            pack_link = f"https://t.me/addstickers/{pack_short_name}"
            await query.message.reply_text(
                f"✅ استیکر شما به پک <a href='{pack_link}'>شما</a> اضافه شد.\n\n"
                f"<b>نکته:</b> برای اطمینان بررسی کنید. اگر اضافه نشده بود، "
                f"روی استیکر بالا کلیک کرده و آن را به صورت دستی به پک خود اضافه کنید.",
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        
        # Clean up pending sticker
        cleanup_pending_sticker(user_id, lookup_key)

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
    application.add_handler(CommandHandler("newpack", new_pack))
    application.add_handler(CommandHandler("addtopack", add_to_pack))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    return application

# Flask routes for Vercel
@app.route('/')
def home():
    return "Telegram Sticker Bot is running!"

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