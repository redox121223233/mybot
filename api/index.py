import os
import logging
import asyncio
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import subprocess
import pydantic_core
import traceback

from fastapi import Request, FastAPI, Response, status
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, BotCommand, BufferedInputFile, InputSticker
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Update

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- تنظیمات اصلی ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()
if not BOT_TOKEN:
    logging.error("BOT_TOKEN not found in environment variables!")
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

CHANNEL_USERNAME = "@redoxbot_sticker"
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919

MAINTENANCE = False
DAILY_LIMIT = 5
BOT_USERNAME = ""

# --- فیلتر کلمات نامناسب ---
FORBIDDEN_WORDS = ["kos", "kir", "kon", "koss", "kiri", "koon"]

# --- حافظه ساده (in-memory) ---
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
        u["day_start"] = today
        u["used_today"] = 0

def _quota_left(u: Dict[str, Any], is_admin: bool) -> int:
    if is_admin:
        return 999
    _reset_daily_if_needed(u)
    used = u.get("used_today", 0)
    return max(0, DAILY_LIMIT - used)

def user(uid: int) -> Dict[str, Any]:
    return USERS.setdefault(uid, {"day_start": _today_start_ts(), "used_today": 0})

def sess(uid: int) -> Dict[str, Any]:
    return SESSIONS.setdefault(uid, {})


# --- ایجاد ربات و دیسپچر ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# --- هندلرها ---
@router.message(CommandStart())
async def send_welcome(message: Message):
    uid = message.from_user.id
    is_admin = (uid == ADMIN_ID)
    
    user(uid)
    sess(uid).clear()
    
    welcome_text = f"""
🎨 **به ربات ساز استیکر خوش آمدید!**

با این ربات می‌توانید:
• استیکر متنی بسازید
• استیکر هوشمند با AI بسازید
• تصاویر را به استیکر تبدیل کنید

{_quota_left(user(uid), is_admin)} استفاده رایگان امروز دارید.

👤 پشتیبانی: {SUPPORT_USERNAME}
📢 کانال: {CHANNEL_USERNAME}
    """
    
    await message.answer(welcome_text, reply_markup=main_menu_kb(is_admin))

def main_menu_kb(is_admin: bool = False) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎨 استیکر متنی ساده", callback_data="simple_mode")
    kb.button(text="🤖 استیکر هوشمند (AI)", callback_data="ai_mode")
    kb.button(text="🖼️ تبدیل عکس به استیکر", callback_data="image_mode")
    
    if is_admin:
        kb.button(text="⚙️ پنل ادمین", callback_data="admin_panel")
    
    kb.button(text="📊 آمار استفاده", callback_data="stats")
    kb.button(text="📢 کانال ما", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
    kb.adjust(2, 1, 1 if is_admin else 0, 1)
    return kb

@router.callback_query(F.data == "simple_mode")
async def simple_mode_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    is_admin = (uid == ADMIN_ID)
    
    sess(uid)["mode"] = "simple"
    sess(uid)["simple"] = {}
    
    await callback.message.answer(
        "📝 **حالت استیکر متنی**\n\n"
        "متن مورد نظر خود را برای استیکر ارسال کنید:",
        reply_markup=back_to_menu_kb(is_admin)
    )
    await callback.answer()

def back_to_menu_kb(is_admin: bool = False) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")
    if is_admin:
        kb.button(text="⚙️ پنل ادمین", callback_data="admin_panel")
    kb.adjust(1)
    return kb

@router.callback_query(F.data == "ai_mode")
async def ai_mode_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    is_admin = (uid == ADMIN_ID)
    
    sess(uid)["mode"] = "ai"
    sess(uid)["ai"] = {}
    
    await callback.message.answer(
        "🤖 **حالت استیکر هوشمند**\n\n"
        "نوع استیکر را انتخاب کنید:",
        reply_markup=ai_type_kb(is_admin)
    )
    await callback.answer()

def ai_type_kb(is_admin: bool = False) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="🖼️ استیکر تصویری", callback_data="ai_image")
    kb.button(text="🎬 استیکر متحرک", callback_data="ai_video")
    kb.button(text="🔙 بازگشت", callback_data="back_to_main")
    if is_admin:
        kb.button(text="⚙️ پنل ادمین", callback_data="admin_panel")
    kb.adjust(2, 1, 1 if is_admin else 0)
    return kb

@router.callback_query(F.data == "image_mode")
async def image_mode_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    is_admin = (uid == ADMIN_ID)
    
    sess(uid)["mode"] = "image"
    sess(uid)["image"] = {}
    
    await callback.message.answer(
        "🖼️ **تبدیل عکس به استیکر**\n\n"
        "عکس مورد نظر خود را ارسال کنید:",
        reply_markup=back_to_menu_kb(is_admin)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    is_admin = (uid == ADMIN_ID)
    
    sess(uid).clear()
    
    await callback.message.answer(
        "🏠 **منوی اصلی**",
        reply_markup=main_menu_kb(is_admin)
    )
    await callback.answer()

@router.callback_query(F.data == "admin_panel")
async def admin_panel_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    
    if uid != ADMIN_ID:
        await callback.answer("❌ دسترسی غیرمجاز!", show_alert=True)
        return
    
    stats_text = f"""
📊 **آمار ربات**

👥 کاربران کل: {len(USERS)}
🔄 کاربران فعال امروز: {sum(1 for u in USERS.values() if u.get('day_start') == _today_start_ts())}
📬 استیکرهای ساخته شده امروز: {sum(u.get('used_today', 0) for u in USERS.values())}
    """
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 بازگشت به منو", callback_data="back_to_main")
    kb.button(text="📢 ارسال پیام همگانی", callback_data="broadcast")
    kb.adjust(1)
    
    await callback.message.answer(stats_text, reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data == "stats")
async def stats_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    is_admin = (uid == ADMIN_ID)
    u = user(uid)
    
    stats_text = f"""
📊 **آمار استفاده شما**

📅 استفاده امروز: {u.get('used_today', 0)} / {DAILY_LIMIT}
🔄 سهمیه باقی‌مانده: {_quota_left(u, is_admin)}
📅 آخرین بازدید: {datetime.fromtimestamp(u.get('day_start', _today_start_ts())).strftime('%Y-%m-%d')}
    """
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 بازگشت به منوی اصلی", callback_data="back_to_main")
    if is_admin:
        kb.button(text="⚙️ پنل ادمین", callback_data="admin_panel")
    kb.adjust(1)
    
    await callback.message.answer(stats_text, reply_markup=kb)
    await callback.answer()

@router.message()
async def handle_message(message: Message):
    uid = message.from_user.id
    is_admin = (uid == ADMIN_ID)
    s = sess(uid)
    mode = s.get("mode", "menu")
    
    # فیلتر کلمات نامناسب
    if message.text:
        text_lower = message.text.lower()
        if any(word in text_lower for word in FORBIDDEN_WORDS):
            await message.answer("❌ لطفاً از کلمات مناسب استفاده کنید.")
            return
    
    if mode == "simple":
        if message.text:
            s["simple"]["text"] = message.text.strip()
            await message.answer("✅ متن دریافت شد. در حال ساخت استیکر...", reply_markup=back_to_menu_kb(is_admin))
            
            # اینجا باید منطق ساخت استیکر ساده اضافه شود
            # فعلاً یک پاسخ آزمایشی می‌دهیم
            await message.answer("🎨 استیکر شما ساخته شد!")
            u = user(uid)
            if not is_admin:
                u["used_today"] = u.get("used_today", 0) + 1
    
    elif mode == "ai":
        if message.text:
            s["ai"]["text"] = message.text.strip()
            await message.answer("🤖 در حال تولید استیکر هوشمند...", reply_markup=back_to_menu_kb(is_admin))
            
            # اینجا باید منطق ساخت استیکر AI اضافه شود
            await message.answer("🎨 استیکر هوشمند شما آماده شد!")
            u = user(uid)
            if not is_admin:
                u["used_today"] = u.get("used_today", 0) + 1
    
    elif mode == "image":
        if message.photo:
            await message.answer("🖼️ عکس دریافت شد. در حال تبدیل به استیکر...", reply_markup=back_to_menu_kb(is_admin))
            
            # اینجا باید منطق تبدیل عکس به استیکر اضافه شود
            await message.answer("✨ عکس به استیکر تبدیل شد!")
            u = user(uid)
            if not is_admin:
                u["used_today"] = u.get("used_today", 0) + 1
    
    else:
        await message.answer("🏠 از منوی اصلی استفاده کنید:", reply_markup=main_menu_kb(is_admin))

# --- تنظیم دیسپچر ---
dp.include_router(router)

# --- اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    logging.info("Webhook received a request!")
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(update=update, bot=bot)
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running on Vercel"}

@app.post("/setWebhook")
async def set_webhook(request: Request):
    webhook_url = f"https://mybot32-5ayzyhqhg-redox121223233s-projects.vercel.app/webhook"
    
    try:
        await bot.set_webhook(url=webhook_url)
        logging.info(f"Webhook set to: {webhook_url}")
        return {"status": "Webhook set successfully", "url": webhook_url}
    except Exception as e:
        logging.error(f"Failed to set webhook: {e}")
        return {"status": "Failed to set webhook", "error": str(e)}