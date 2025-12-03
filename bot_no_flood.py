import asyncio
import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import logging
import traceback
import time

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
        u["count"] = 0
        u["day_start"] = today

def _check_forbidden(text: str) -> bool:
    text_lower = text.lower()
    return any(word in text_lower for word in FORBIDDEN_WORDS)

def _get_user(user_id: int) -> Dict[str, Any]:
    if user_id not in USERS:
        USERS[user_id] = {"count": 0, "day_start": _today_start_ts()}
    _reset_daily_if_needed(USERS[user_id])
    return USERS[user_id]

def _can_create_sticker(user_id: int) -> bool:
    u = _get_user(user_id)
    if u["count"] >= DAILY_LIMIT:
        return False
    u["count"] += 1
    return True

# ================ توابع استیکر =================
async def _create_text_sticker(text: str, width: int = 512, height: int = 512, 
                             font_size: int = 48, bg_color: str = "#2E2E2E", 
                             text_color: str = "#FFFFFF") -> BytesIO:
    try:
        img = Image.new('RGBA', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except Exception:
            bidi_text = text
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), bidi_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), bidi_text, font=font, fill=text_color)
        
        buffer = BytesIO()
        img.save(buffer, format='WEBP')
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        logger.error(f"Error creating sticker: {e}")
        raise

# ================ روتر و هندلرها =================
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = _get_user(message.from_user.id)
    remaining = DAILY_LIMIT - user["count"]
    
    text = (
        "🎨 **به ربات استیکر ساز خوش آمدید!**\n\n"
        "هر متنی را بفرستید تا به استیکر تبدیل شود.\n\n"
        f"📊 **محدودیت روزانه:** {user['count']}/{DAILY_LIMIT}\n"
        f"🔄 **مانده:** {remaining} استیکر\n\n"
        "⚙️ **دستورات:**\n"
        "/start - شروع\n"
        "/help - راهنما"
    )
    
    await message.answer(text)

@router.message(CommandStart(), F.text.startswith("create_"))
async def cmd_start_create(message: Message):
    user_id = message.from_user.id
    
    if user_id not in SESSIONS:
        SESSIONS[user_id] = {}
    
    SESSIONS[user_id]['mode'] = 'text'
    
    text = (
        "✍️ **حالت متن انتخاب شد**\n\n"
        "متن مورد نظر خود را ارسال کنید تا به استیکر تبدیل شود."
    )
    
    await message.answer(text)

@router.message(CommandStart(), F.text.startswith("custom_"))
async def cmd_start_custom(message: Message):
    user_id = message.from_user.id
    
    if user_id not in SESSIONS:
        SESSIONS[user_id] = {}
    
    SESSIONS[user_id]['mode'] = 'custom'
    SESSIONS[user_id]['step'] = 'background'
    
    text = (
        "🎨 **حالت سفارشی انتخاب شد**\n\n"
        "مرحله ۱: رنگ پس‌زمینه را انتخاب کنید:\n"
        "• سفید (white)\n"
        "• مشکی (black)\n"
        "• آبی (blue)\n"
        "• قرمز (red)\n"
        "• سبز (green)\n"
        "• یا کد HEX مانند #FF5733"
    )
    
    await message.answer(text)

async def cmd_help(message: Message):
    text = (
        "📖 **راهنمای ربات استیکر ساز**\n\n"
        "🔹 **ساخت استیکر ساده:**\n"
        "متن خود را ارسال کنید\n\n"
        "🔹 **استیکر سفارشی:**\n"
        "برای استیکر با تنظیمات دلخواه از دستور زیر استفاده کنید:\n"
        "/custom\n\n"
        "🔹 **محدودیت‌ها:**\n"
        f"• روزانه {DAILY_LIMIT} استیکر\n"
        "• کلمات نامناسب فیلتر می‌شوند\n\n"
        f"📢 **کانال:** {CHANNEL_USERNAME}\n"
        f"👤 **پشتیبانی:** {SUPPORT_USERNAME}"
    )
    
    await message.answer(text)

# ثبت دستور help
router.message.register(cmd_help, Command('help'))

@router.message()
async def handle_text(message: Message):
    if MAINTENANCE:
        await message.answer("🔧 ربات در حال تعمیر است. لطفاً بعداً تلاش کنید.")
        return
    
    user_id = message.from_user.id
    text = message.text or message.caption
    
    if not text:
        await message.answer("❌ فقط متن قبول می‌شود.")
        return
    
    if len(text) > 100:
        await message.answer("❌ متن باید کمتر از ۱۰۰ کاراکتر باشد.")
        return
    
    if _check_forbidden(text):
        await message.answer("❌ متن نامناسب است.")
        return
    
    if not _can_create_sticker(user_id):
        user = _get_user(user_id)
        await message.answer(f"❌ به محدودیت روزانه ({DAILY_LIMIT}) رسیدید. فردا دوباره تلاش کنید.")
        return
    
    try:
        await message.answer("🎨 در حال ساخت استیکر...")
        
        sticker_buffer = await _create_text_sticker(text)
        
        input_file = BufferedInputFile(
            file=sticker_buffer.read(),
            filename=f"sticker_{int(time.time())}.webp"
        )
        
        await message.answer_sticker(sticker=input_file)
        
        user = _get_user(user_id)
        remaining = DAILY_LIMIT - user["count"]
        await message.answer(f"✅ استیکر ساخته شد! 🎉\n🔄 استیکرهای باقی‌مانده: {remaining}")
        
    except Exception as e:
        logger.error(f"Error processing sticker: {e}")
        await message.answer("❌ خطا در ساخت استیکر. لطفاً دوباره تلاش کنید.")

# Global variables
bot = None
dp = None

async def create_bot_without_commands():
    """
    Create bot WITHOUT setting commands to avoid flood control
    """
    global bot, dp
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set")
        return None
    
    try:
        # Create bot with proper settings
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML
            )
        )
        
        # Create dispatcher
        dp = Dispatcher()
        dp.include_router(router)
        
        logger.info("Bot created successfully (NO COMMANDS SET)")
        
        # CRITICAL: DO NOT set bot commands during initialization
        # This prevents the flood control error
        logger.info("Skipping bot commands setup to avoid flood control")
        
        return bot
        
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        return None

async def set_bot_commands_delayed():
    """
    Set bot commands after a delay to avoid flood control
    Call this function separately after bot is running
    """
    global bot
    
    if not bot:
        logger.warning("Bot not initialized, cannot set commands")
        return False
    
    try:
        # Wait a bit to avoid flood control
        await asyncio.sleep(2)
        
        # Try to set commands with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await bot.set_my_commands([
                    BotCommand(command="start", description="شروع ربات"),
                    BotCommand(command="help", description="راهنما"),
                ])
                logger.info("Bot commands set successfully")
                return True
                
            except Exception as cmd_error:
                logger.warning(f"Command setup attempt {attempt + 1} failed: {cmd_error}")
                if attempt < max_retries - 1:
                    # Exponential backoff: wait longer each time
                    wait_time = 10 * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Failed to set bot commands after all retries")
        
        return False
        
    except Exception as e:
        logger.error(f"Error in delayed command setup: {e}")
        return False

# Export functions
__all__ = ['bot', 'dp', 'router', 'create_bot_without_commands', 'set_bot_commands_delayed']