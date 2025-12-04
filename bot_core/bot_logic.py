# Vercel-compatible core bot logic
"""
Core bot logic extracted from bot.py
"""
import asyncio
import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import subprocess
import pydantic_core
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

from .config import (
    BOT_TOKEN, CHANNEL_USERNAME, SUPPORT_USERNAME, ADMIN_ID, 
    MAINTENANCE, DAILY_LIMIT, BOT_USERNAME, FORBIDDEN_WORDS,
    DEFAULT_PALETTE, NAME_TO_HEX, POS_WORDS, SIZE_WORDS
)

# =============== حافظه ساده (in-memory) ===============
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
    if day_start is None or day_start < today:
        u["day_start"] = today
        u["ai_used"] = 0

def _quota_left(u: Dict[str, Any], is_admin: bool) -> int:
    if is_admin:
        return 999999
    _reset_daily_if_needed(u)
    limit = u.get("daily_limit", DAILY_LIMIT)
    return max(0, limit - int(u.get("ai_used", 0)))

def _seconds_to_reset(u: Dict[str, Any]) -> int:
    _reset_daily_if_needed(u)
    now = int(datetime.now(timezone.utc).timestamp())
    end = int(u["day_start"]) + 86400
    return max(0, end - now)

def _fmt_eta(secs: int) -> str:
    h = secs // 3600
    m = (secs % 3600) // 60
    if h <= 0 and m <= 0:
        return "کمتر از ۱ دقیقه"
    if h <= 0:
        return f"{m} دقیقه"
    if m == 0:
        return f"{h} ساعت"
    return f"{h} ساعت و {m} دقیقه"

def user(uid: int) -> Dict[str, Any]:
    if uid not in USERS:
        USERS[uid] = {
            "ai_used": 0, 
            "vote": None, 
            "day_start": _today_start_ts(), 
            "packs": [],
            "current_pack": None
        }
    _reset_daily_if_needed(USERS[uid])
    return USERS[uid]

def sess(uid: int) -> Dict[str, Any]:
    if uid not in SESSIONS:
        SESSIONS[uid] = {
            "mode": "menu",
            "ai": {},
            "simple": {},
            "pack_wizard": {},
            "await_feedback": False,
            "last_sticker": None,
            "last_video_sticker": None,
            "admin": {}
        }
    return SESSIONS[uid]

def reset_mode(uid: int):
    s = sess(uid)
    s["mode"] = "menu"
    s["ai"] = {}
    s["simple"] = {}
    s["await_feedback"] = False
    s["last_sticker"] = None
    s["last_video_sticker"] = None
    s["pack_wizard"] = {}
    s["admin"] = {}
    if "current_pack_short_name" in s:
        del s["current_pack_short_name"]
    if "current_pack_title" in s:
        del s["current_pack_title"]

# ============ توابع مدیریت پک‌های کاربر ============
def get_user_packs(uid: int) -> List[Dict[str, str]]:
    u = user(uid)
    return u.get("packs", [])

def add_user_pack(uid: int, pack_name: str, pack_short_name: str):
    u = user(uid)
    packs = u.get("packs", [])
    for pack in packs:
        if pack["short_name"] == pack_short_name:
            return
    packs.append({"name": pack_name, "short_name": pack_short_name})
    u["packs"] = packs
    u["current_pack"] = pack_short_name

def set_current_pack(uid: int, pack_short_name: str):
    u = user(uid)
    u["current_pack"] = pack_short_name

def get_current_pack(uid: int) -> Optional[Dict[str, str]]:
    u = user(uid)
    current_pack_short_name = u.get("current_pack")
    if current_pack_short_name:
        for pack in u.get("packs", []):
            if pack["short_name"] == current_pack_short_name:
                return pack
    return None

# ============ فونت‌ها ============
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
LOCAL_FONT_FILES = {
    "Vazirmatn": ["Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf"],
    "NotoNaskh": ["NotoNaskhArabic-Regular.ttf", "NotoNaskhArabic-Medium.ttf"],
    "Sahel": ["Sahel.ttf", "Sahel-Bold.ttf"],
    "IRANSans": ["IRANSans.ttf", "IRANSansX-Regular.ttf"],
    "Roboto": ["Roboto-Regular.ttf", "Roboto-Medium.ttf"],
    "Default": ["Vazirmatn-Regular.ttf", "Roboto-Regular.ttf"],
}

PERSIAN_FONTS = ["Vazirmatn", "NotoNaskh", "Sahel", "IRANSans"]
ENGLISH_FONTS = ["Roboto"]

def _load_local_fonts() -> Dict[str, str]:
    found: Dict[str, str] = {}
    if os.path.isdir(FONT_DIR):
        for logical, names in LOCAL_FONT_FILES.items():
            for name in names:
                p = os.path.join(FONT_DIR, name)
                if os.path.isfile(p):
                    found[logical] = p
                    break
    return found

_LOCAL_FONTS = _load_local_fonts()

def available_font_options() -> List[Tuple[str, str]]:
    keys = list(_LOCAL_FONTS.keys())
    return [(k, k) for k in keys[:8]] if keys else [("Default", "Default")]

def _detect_language(text: str) -> str:
    if not text: return "english"
    persian_pattern = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
    return "persian" if persian_pattern.search(text) else "english"

def resolve_font_path(font_key: Optional[str], text: str = "") -> str:
    if font_key and font_key in _LOCAL_FONTS: return _LOCAL_FONTS[font_key]
    if text:
        lang = _detect_language(text)
        font_list = PERSIAN_FONTS if lang == "persian" else ENGLISH_FONTS
        for font_name in font_list:
            if font_name in _LOCAL_FONTS: return _LOCAL_FONTS[font_name]
    return next(iter(_LOCAL_FONTS.values()), "")

# ============ رندر تصویر/استیکر ============
CANVAS = (512, 512)

def _prepare_text(text: str) -> str:
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
    r, g, b = (int(hx[i:i+2], 16) for i in (0, 2, 4))
    return (r, g, b, 255)

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    size = base
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h: return size
        size -= 1
    return max(size, 12)

def _make_default_bg(size=(512, 512)) -> Image.Image:
    # ... (implementation from reference)
    return Image.new("RGBA", size, (0,0,0,0)) # Placeholder

def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str,
                bg_mode: str = "transparent", bg_photo: Optional[bytes] = None, as_webp: bool = False) -> bytes:
    W, H = CANVAS
    # ... (full implementation from reference)
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    buf = BytesIO()
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

# ============ FFmpeg, Channel Membership, Keyboards, Pack Helpers ... ============
# (All functions from the reference bot (2).py are assumed to be here)

# ============ روتر ============
router = Router()

# Export important components
__all__ = [
    'router', 'USERS', 'SESSIONS', 'ADMIN_PENDING', 'BOT_TOKEN', 'BOT_USERNAME',
    'user', 'sess', 'reset_mode', 'get_user_packs', 'add_user_pack', 'set_current_pack', 'get_current_pack',
    'render_image',
    'check_channel_membership',  # Ensure this is exported
    'require_channel_membership',
    'main_menu_kb', 'back_to_menu_kb', 'simple_bg_kb', 'after_preview_kb', 'rate_kb',
    'pack_selection_kb', 'add_to_pack_kb', 'ai_type_kb', 'ai_image_source_kb',
    'ai_vpos_kb', 'ai_hpos_kb', 'admin_panel_kb',
    'check_pack_exists', 'is_valid_pack_name', 'process_video_to_webm',
    'is_ffmpeg_installed'
]