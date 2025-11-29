import asyncio
import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import logging
import traceback

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, BotCommand, BufferedInputFile, InputSticker
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============== تنظیمات ===============
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    logger.warning("BOT_TOKEN not set in environment variables")

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@redoxbot_sticker")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@onedaytoalive")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6053579919"))

MAINTENANCE = os.getenv("MAINTENANCE", "false").lower() == "true"
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

# ============ فیلتر کلمات نامناسب ============
FORBIDDEN_WORDS = ["kos", "kir", "kon", "koss", "kiri", "koon"]

# ============ حافظه ساده (in-memory) ============
USERS: Dict[int, Dict[str, Any]] = {}
SESSIONS: Dict[int, Dict[str, Any]] = {}
ADMIN_PENDING: Dict[int, Dict[str, Any]] = {}

def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return int(midnight.timestamp())

def _reset_daily_if_needed(u: Dict[str, Any]):
    day_start = u.get("day_start")
    today = _today_start_ts()
    if day_start != today:
        u["daily_count"] = 0
        u["day_start"] = today

def _get_user_limit(user_id: int) -> int:
    if user_id == ADMIN_ID:
        return 9999
    u = USERS.get(user_id, {"daily_count": 0, "day_start": _today_start_ts()})
    _reset_daily_if_needed(u)
    USERS[user_id] = u
    return max(0, DAILY_LIMIT - u["daily_count"])

def _increment_usage(user_id: int):
    if user_id == ADMIN_ID:
        return
    u = USERS.get(user_id, {"daily_count": 0, "day_start": _today_start_ts()})
    _reset_daily_if_needed(u)
    u["daily_count"] += 1
    USERS[user_id] = u

def _contains_forbidden(text: str) -> bool:
    text = text.lower()
    return any(word in text for word in FORBIDDEN_WORDS)

async def check_membership(user_id: int, bot: Bot) -> bool:
    """Check if user is member of channel"""
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Membership check failed: {e}")
        return True  # Allow if can't check

# Create router
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    # Check maintenance
    if MAINTENANCE and user_id != ADMIN_ID:
        await message.answer("🔧 ربات در حال تعمیر است. لطفاً بعداً تلاش کنید.")
        return
    
    # Initialize user data
    if user_id not in USERS:
        USERS[user_id] = {"daily_count": 0, "day_start": _today_start_ts()}
    
    # Check channel membership
    is_member = await check_membership(user_id, bot)
    if not is_member:
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="📺 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        keyboard.button(text="✅ عضو شدم", callback_data="check_join")
        await message.answer(
            "برای استفاده از ربات، لطفاً در کانال عضو شوید:\n\n"
            "Please join the channel to use the bot:",
            reply_markup=keyboard.as_markup()
        )
        return
    
    # Show main menu
    await show_main_menu(message)

async def show_main_menu(message: Message):
    user_id = message.from_user.id
    remaining = _get_user_limit(user_id)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🎨 ساخت استیکر متنی", callback_data="text_sticker")
    keyboard.button(text="📸 ساخت استیکر تصویری", callback_data="image_sticker")
    keyboard.button(text="⚙️ تنظیمات", callback_data="settings")
    keyboard.adjust(2, 1)
    
    welcome_text = (
        "🎭 *به ربات ساخت استیکر خوش آمدید!*\n\n"
        f"📊 سهمیه روزانه شما: {remaining} استیکر\n"
        "🎯 یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    
    await message.answer(welcome_text, reply_markup=keyboard.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    is_member = await check_membership(user_id, bot)
    
    if is_member:
        await callback.answer("✅ عضویت شما تایید شد!", show_alert=True)
        await show_main_menu(callback.message)
    else:
        await callback.answer("❌ شما هنوز عضو کانال نشده‌اید!", show_alert=True)

@router.callback_query(F.data == "text_sticker")
async def text_sticker_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    remaining = _get_user_limit(user_id)
    
    if remaining <= 0:
        await callback.answer("❌ سهمیه روزانه شما تمام شده!", show_alert=True)
        return
    
    # Set session state
    SESSIONS[user_id] = {"state": "waiting_text", "step": 1}
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 بازگشت", callback_data="back_to_main")
    
    await callback.message.edit_text(
        "✏️ *متن مورد نظر خود را ارسال کنید*\n\n"
        "متن شما به استیکر تبدیل خواهد شد.\n"
        "می‌توانید از ایموجی هم استفاده کنید.",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "image_sticker")
async def image_sticker_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    remaining = _get_user_limit(user_id)
    
    if remaining <= 0:
        await callback.answer("❌ سهمیه روزانه شما تمام شده!", show_alert=True)
        return
    
    # Set session state
    SESSIONS[user_id] = {"state": "waiting_image", "step": 1}
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 بازگشت", callback_data="back_to_main")
    
    await callback.message.edit_text(
        "📸 *تصویر مورد نظر خود را ارسال کنید*\n\n"
        "تصویر باید فرمت JPG یا PNG داشته باشد.\n"
        "سایز بهینه: 512x512 پیکسل",
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "settings")
async def settings_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    remaining = _get_user_limit(user_id)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📊 آمار استفاده", callback_data="usage_stats")
    keyboard.button(text="🆘 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")
    keyboard.button(text="🔙 بازگشت", callback_data="back_to_main")
    keyboard.adjust(2, 1)
    
    settings_text = (
        "⚙️ *تنظیمات ربات*\n\n"
        f"📊 سهمیه روزانه: {remaining}/{DAILY_LIMIT}\n"
        f"👤 وضعیت: {'ادمین' if user_id == ADMIN_ID else 'کاربر عادی'}\n"
        f"🔧 وضعیت ربات: {'در تعمیر' if MAINTENANCE else 'آماده به کار'}"
    )
    
    await callback.message.edit_text(
        settings_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery):
    await show_main_menu(callback.message)
    await callback.answer()

@router.callback_query(F.data == "usage_stats")
async def usage_stats_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = USERS.get(user_id, {"daily_count": 0, "day_start": _today_start_ts()})
    
    stats_text = (
        "📊 *آمار استفاده شما*\n\n"
        f"📝 تعداد استیکرهای ساخته شده امروز: {user_data['daily_count']}\n"
        f"🎯 سهمیه باقیمانده: {_get_user_limit(user_id)}\n"
        f"📅 تاریخ شروع: {datetime.fromtimestamp(user_data['day_start']).strftime('%Y-%m-%d')}"
    )
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 بازگشت", callback_data="settings")
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=keyboard.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message()
async def handle_message(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    # Check if user has active session
    session = SESSIONS.get(user_id)
    if not session:
        await cmd_start(message, bot)
        return
    
    if session["state"] == "waiting_text":
        await handle_text_input(message, user_id)
    elif session["state"] == "waiting_image":
        await handle_image_input(message, user_id)

async def handle_text_input(message: Message, user_id: int):
    text = message.text or message.caption
    
    if not text:
        await message.answer("❌ لطفاً متنی ارسال کنید.")
        return
    
    if _contains_forbidden(text):
        await message.answer("❌ متن شما حاوی کلمات نامناسب است.")
        return
    
    # Check limit
    if _get_user_limit(user_id) <= 0:
        await message.answer("❌ سهمیه روزانه شما تمام شده!")
        return
    
    try:
        # Create text sticker
        sticker_file = await create_text_sticker(text)
        
        # Send sticker
        await message.answer_sticker(sticker_file)
        
        # Increment usage
        _increment_usage(user_id)
        
        # Clear session
        if user_id in SESSIONS:
            del SESSIONS[user_id]
        
        # Show success message
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🎨 استیکر دیگر", callback_data="text_sticker")
        keyboard.button(text="🏠 منوی اصلی", callback_data="back_to_main")
        keyboard.adjust(1)
        
        remaining = _get_user_limit(user_id)
        await message.answer(
            f"✅ استیکر با موفقیت ساخته شد!\n📊 سهمیه باقیمانده: {remaining}",
            reply_markup=keyboard.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error creating text sticker: {e}")
        await message.answer("❌ خطا در ساخت استیکر. لطفاً دوباره تلاش کنید.")

async def handle_image_input(message: Message, user_id: int):
    if not message.photo and not message.document:
        await message.answer("❌ لطفاً یک تصویر ارسال کنید.")
        return
    
    # Check limit
    if _get_user_limit(user_id) <= 0:
        await message.answer("❌ سهمیه روزانه شما تمام شده!")
        return
    
    try:
        # Get photo file
        if message.photo:
            file_id = message.photo[-1].file_id  # Get highest quality
        else:
            # Handle document
            file_id = message.document.file_id
        
        # Download and process image
        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        # Create image sticker
        sticker_file = await create_image_sticker(file_bytes)
        
        # Send sticker
        await message.answer_sticker(sticker_file)
        
        # Increment usage
        _increment_usage(user_id)
        
        # Clear session
        if user_id in SESSIONS:
            del SESSIONS[user_id]
        
        # Show success message
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="📸 تصویر دیگر", callback_data="image_sticker")
        keyboard.button(text="🏠 منوی اصلی", callback_data="back_to_main")
        keyboard.adjust(1)
        
        remaining = _get_user_limit(user_id)
        await message.answer(
            f"✅ استیکر با موفقیت ساخته شد!\n📊 سهمیه باقیمانده: {remaining}",
            reply_markup=keyboard.as_markup()
        )
        
    except Exception as e:
        logger.error(f"Error creating image sticker: {e}")
        await message.answer("❌ خطا در ساخت استیکر. لطفاً دوباره تلاش کنید.")

async def create_text_sticker(text: str) -> BufferedInputFile:
    """Create a text sticker"""
    # Image settings
    width, height = 512, 512
    background_color = (255, 255, 255)  # White
    text_color = (0, 0, 0)  # Black
    
    # Create image
    img = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load font
    try:
        font_size = 40
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
    
    # Process Arabic/Persian text if needed
    try:
        if any('\u0600' <= c <= '\u06FF' for c in text):
            text = arabic_reshaper.reshape(text)
            text = get_display(text)
    except:
        pass  # Fallback to original text
    
    # Calculate text position (center)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw text
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return BufferedInputFile(buffer.read(), filename="sticker.png")

async def create_image_sticker(image_bytes: bytes) -> BufferedInputFile:
    """Create an image sticker"""
    # Open image
    img = Image.open(BytesIO(image_bytes))
    
    # Convert to RGBA if needed
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Resize to 512x512
    img = img.resize((512, 512), Image.Resampling.LANCZOS)
    
    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return BufferedInputFile(buffer.read(), filename="sticker.png")

# Create bot instance
bot = None
dp = None

def create_bot():
    """Create bot instance with optimized settings"""
    global bot, dp
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set")
        return False
    
    try:
        # Create bot with optimized settings for Vercel
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        )
        
        # Create dispatcher
        dp = Dispatcher()
        dp.include_router(router)
        
        # Set bot commands
        await bot.set_my_commands([
            BotCommand(command="start", description="شروع ربات"),
            BotCommand(command="help", description="راهنما"),
        ])
        
        logger.info("Bot created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        return False

# Initialize function
async def init():
    """Initialize the bot"""
    return await create_bot()

# Export for use in api/index.py
__all__ = ['bot', 'dp', 'init', 'router']