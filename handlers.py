# --- handlers.py ---
import os
import re
import asyncio
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display
from aiogram import F, Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

# =============== پیکربندی ===============
CHANNEL_USERNAME = "@redoxbot_sticker"
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919
DAILY_LIMIT = 5
BOT_USERNAME = ""

# ============ حافظه ساده (in-memory) ============
USERS: Dict[int, Dict[str, Any]] = {}
SESSIONS: Dict[int, Dict[str, Any]] = {}

def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return int(midnight.timestamp())

def _reset_daily_if_needed(u: Dict[str, Any]):
    day_start = u.get("day_start")
    today = _today_start_ts()
    if day_start is None or day_start < today:
        u["day_start"] = today
        u["ai_used"] = 0

def _quota_left(u: Dict[str, Any], is_admin: bool) -> int:
    if is_admin:
        return 999999
    _reset_daily_if_needed(u)
    limit = u.get("daily_limit", DAILY_LIMIT)
    return max(0, limit - int(u.get("ai_used", 0)))

def user(uid: int) -> Dict[str, Any]:
    if uid not in USERS:
        USERS[uid] = {
            "ai_used": 0, "vote": None, "day_start": _today_start_ts(),
            "packs": [], "current_pack": None
        }
    _reset_daily_if_needed(USERS[uid])
    return USERS[uid]

def sess(uid: int) -> Dict[str, Any]:
    if uid not in SESSIONS:
        SESSIONS[uid] = {
            "mode": "menu", "ai": {}, "simple": {}, "pack_wizard": {},
            "await_feedback": False, "last_sticker": None, "admin": {}
        }
    return SESSIONS[uid]

# ============ توابع کمکی کیبورد ============
def main_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر ساده", callback_data="menu:simple")
    kb.button(text="استیکر ساز پیشرفته", callback_data="menu:ai")
    kb.button(text="سهمیه امروز", callback_data="menu:quota")
    kb.button(text="راهنما", callback_data="menu:help")
    kb.button(text="پشتیبانی", callback_data="menu:support")
    if is_admin:
        kb.button(text="پنل ادمین", callback_data="menu:admin")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

def back_to_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="بازگشت به منو", callback_data="menu:home")
    if is_admin:
        kb.button(text="پنل ادمین", callback_data="menu:admin")
    kb.adjust(1)
    return kb.as_markup()

# ============ ثبت هندلرها ============
def register_handlers(dp: Dispatcher):
    router = Router()
    
    @router.message(CommandStart())
    async def on_start(message: types.Message, bot: Bot):
        # برای سادگی، در این مرحله فقط پیام خوشامدگویی را ارسال می‌کنیم
        is_admin = (message.from_user.id == ADMIN_ID)
        await message.answer("سلام! ربات با aiogram روی Vercel کار می‌کند! ✅", reply_markup=main_menu_kb(is_admin))

    @router.callback_query(F.data == "menu:home")
    async def on_home(cb: types.CallbackQuery, bot: Bot):
        is_admin = (cb.from_user.id == ADMIN_ID)
        await cb.message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
        await cb.answer()

    # ... بقیه هندلرهای شما را می‌توانید به همین شکل اضافه کنید ...
    # برای مثال:
    # @router.callback_query(F.data == "menu:simple")
    # async def on_simple(cb: types.CallbackQuery, bot: Bot):
    #     await cb.message.answer("ورود به بخش استیکر ساده...")
    #     await cb.answer()

    dp.include_router(router)
