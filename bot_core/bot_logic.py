"""
Core bot logic, data structures, and keyboards.
Fully refactored from the reference script `bot (2).py` to ensure all functionality is preserved.
"""
import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import subprocess
import traceback

from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

from .config import ADMIN_ID, CHANNEL_USERNAME, DAILY_LIMIT, SUPPORT_USERNAME, FORBIDDEN_WORDS

# --- In-memory Storage ---
USERS: Dict[int, Dict[str, Any]] = {}
SESSIONS: Dict[int, Dict[str, Any]] = {}
ADMIN_PENDING: Dict[int, Dict[str, Any]] = {}

# --- User and Session Management ---
def _today_start_ts() -> int:
    now = datetime.now(timezone.utc)
    return int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())

def _reset_daily_if_needed(u: Dict[str, Any]):
    if u.get("day_start", 0) < _today_start_ts():
        u["day_start"] = _today_start_ts()
        u["ai_used"] = 0

def _quota_left(u: Dict[str, Any], is_admin: bool) -> int:
    if is_admin: return 999999
    _reset_daily_if_needed(u)
    limit = u.get("daily_limit", DAILY_LIMIT)
    return max(0, limit - u.get("ai_used", 0))

def _seconds_to_reset(u: Dict[str, Any]) -> int:
    _reset_daily_if_needed(u)
    now = int(datetime.now(timezone.utc).timestamp())
    end_of_day = u["day_start"] + 86400
    return max(0, end_of_day - now)

def _fmt_eta(secs: int) -> str:
    h, m = divmod(secs, 3600)
    m //= 60
    if h > 0: return f"{h} ساعت و {m} دقیقه"
    if m > 0: return f"{m} دقیقه"
    return "کمتر از یک دقیقه"

def user(uid: int) -> Dict[str, Any]:
    if uid not in USERS:
        USERS[uid] = {"ai_used": 0, "vote": None, "day_start": _today_start_ts(), "packs": [], "current_pack": None}
    _reset_daily_if_needed(USERS[uid])
    return USERS[uid]

def sess(uid: int) -> Dict[str, Any]:
    if uid not in SESSIONS:
        SESSIONS[uid] = {"mode": "menu", "ai": {}, "simple": {}, "pack_wizard": {}, "await_feedback": False, "last_sticker": None, "last_video_sticker": None, "admin": {}}
    return SESSIONS[uid]

def reset_mode(uid: int):
    SESSIONS[uid] = {"mode": "menu", "ai": {}, "simple": {}, "pack_wizard": {}, "await_feedback": False, "last_sticker": None, "last_video_sticker": None, "admin": {}}

# --- Sticker Pack Management ---
def get_user_packs(uid: int) -> List[Dict[str, str]]: return user(uid).get("packs", [])
def add_user_pack(uid: int, pack_name: str, pack_short_name: str):
    u = user(uid)
    packs = u.get("packs", [])
    if not any(p["short_name"] == pack_short_name for p in packs):
        packs.append({"name": pack_name, "short_name": pack_short_name})
    u["current_pack"] = pack_short_name
def set_current_pack(uid: int, pack_short_name: str): user(uid)["current_pack"] = pack_short_name
def get_current_pack(uid: int) -> Optional[Dict[str, str]]:
    short_name = user(uid).get("current_pack")
    return next((p for p in get_user_packs(uid) if p["short_name"] == short_name), None)

async def check_pack_exists(bot: Bot, short_name: str) -> bool:
    try:
        await bot.get_sticker_set(name=short_name)
        return True
    except TelegramBadRequest: return False
def is_valid_pack_name(name: str) -> bool: return bool(re.match(r"^[a-z][a-z0-9_]{0,49}(?<!_)(?<!__)$", name))


# --- Data and NLU ---
# DEFAULT_PALETTE is now in config.py

# --- Font and Image Rendering ---
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
LOCAL_FONT_FILES = {"Vazirmatn": "Vazirmatn-Regular.ttf", "NotoNaskh": "NotoNaskhArabic-Regular.ttf", "Sahel": "Sahel.ttf", "IRANSans": "IRANSans.ttf", "Roboto": "Roboto-Regular.ttf", "Default": "Vazirmatn-Regular.ttf"}
_LOCAL_FONTS = {k: os.path.join(FONT_DIR, v) for k, v in LOCAL_FONT_FILES.items() if os.path.exists(os.path.join(FONT_DIR, v))}
def resolve_font_path(font_key: Optional[str], text: str = "") -> str:
    if font_key and font_key in _LOCAL_FONTS: return _LOCAL_FONTS[font_key]
    is_persian = any('\u0600' <= char <= '\u06FF' for char in text)
    return _LOCAL_FONTS.get("Vazirmatn" if is_persian else "Roboto", next(iter(_LOCAL_FONTS.values()), ""))

def _prepare_text(text: str) -> str: return get_display(arabic_reshaper.reshape(text))

def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str, bg_mode: str = "transparent", bg_photo: Optional[bytes] = None, as_webp: bool = False) -> bytes:
    W, H = 512, 512
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    if bg_mode == "default":
        img = Image.new("RGBA", (W, H), (20, 20, 35, 255))
    elif bg_photo:
        try: img = Image.open(BytesIO(bg_photo)).convert("RGBA").resize((W, H))
        except: pass

    draw = ImageDraw.Draw(img)
    color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
    padding = 40
    box_w, box_h = W - 2*padding, H - 2*padding
    base_size = {"small": 64, "medium": 96, "large": 128}.get(size_key, 96)
    font_path = resolve_font_path(font_key, text)
    txt = _prepare_text(text)

    size = base_size
    while size > 12:
        font = ImageFont.truetype(font_path, size=size)
        bbox = draw.textbbox((0,0), txt, font=font)
        if (bbox[2]-bbox[0] <= box_w) and (bbox[3]-bbox[1] <= box_h): break
        size -= 1
    font = ImageFont.truetype(font_path, size=size)
    bbox = draw.textbbox((0,0), txt, font=font)
    text_width, text_height = bbox[2]-bbox[0], bbox[3]-bbox[1]

    y = {"top": padding, "bottom": H - padding - text_height}.get(v_pos, (H - text_height) / 2)
    x = {"left": padding, "right": W - padding - text_width}.get(h_pos, W / 2)
    anchor = "mm" if h_pos == "center" else "lm"
    draw.text((x, y), txt, font=font, fill=color, anchor=anchor, stroke_width=2, stroke_fill=(0,0,0,220))

    buf = BytesIO() 
    if as_webp:
        img.save(buf, format="WEBP", quality=90)
    else:
        # PNG with optimization for Telegram stickers
        img.save(buf, format="PNG", optimize=True, compress_level=9)
    
    result = buf.getvalue()
    
    # Check if file size is too large for Telegram
    if not as_webp and len(result) > 64 * 1024:  # 64 KB limit for PNG stickers
        # Try to reduce quality by resizing and re-compressing
        try:
            # Create a slightly smaller image
            smaller_img = img.resize((400, 400), Image.Resampling.LANCZOS)
            buf2 = BytesIO()
            smaller_img.save(buf2, format="PNG", optimize=True, compress_level=9)
            result = buf2.getvalue()
            
            # If still too large, try even smaller
            if len(result) > 64 * 1024:
                even_smaller_img = img.resize((350, 350), Image.Resampling.LANCZOS)
                buf3 = BytesIO()
                even_smaller_img.save(buf3, format="PNG", optimize=True, compress_level=9)
                result = buf3.getvalue()
        except Exception:
            pass  # Keep original if optimization fails
    
    return result

# --- FFmpeg ---
def is_ffmpeg_installed() -> bool:
    try: subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True); return True
    except: return False

async def process_video_to_webm(video_bytes: bytes) -> Optional[bytes]:
    if not is_ffmpeg_installed(): return None
    try:
        p = await asyncio.create_subprocess_exec('ffmpeg', '-i', '-', '-f', 'webm', '-c:v', 'libvpx-vp9', '-b:v', '1M', '-crf', '30', '-', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await p.communicate(input=video_bytes)
        if p.returncode != 0: print(f"FFmpeg error: {stderr.decode()}"); return None
        return stdout
    except Exception as e: print(f"Video processing error: {e}"); return None

# --- Channel Membership ---
async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    if not CHANNEL_USERNAME: return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception: return False

async def require_channel_membership(message: Message, bot: Bot) -> bool:
    if await check_channel_membership(bot, message.from_user.id): return True
    kb = InlineKeyboardBuilder(); kb.button(text="عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"); kb.button(text="بررسی عضویت", callback_data="check_membership"); kb.adjust(1)
    try: await message.answer(f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.", reply_markup=kb.as_markup())
    except TelegramForbiddenError: print(f"User {message.from_user.id} has blocked the bot.")
    return False

# --- Keyboards ---
def main_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder(); kb.button(text="استیکر ساده", callback_data="menu:simple"); kb.button(text="استیکر ساز پیشرفته", callback_data="menu:ai"); kb.button(text="سهمیه امروز", callback_data="menu:quota"); kb.button(text="راهنما", callback_data="menu:help"); kb.button(text="پشتیبانی", callback_data="menu:support");
    if is_admin: kb.button(text="پنل ادمین", callback_data="menu:admin")
    kb.adjust(2, 2, 2, 1); return kb.as_markup()
def back_to_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder(); kb.button(text="بازگشت به منو", callback_data="menu:home");
    if is_admin: kb.button(text="پنل ادمین", callback_data="menu:admin")
    return kb.as_markup()
def simple_bg_kb():
    kb = InlineKeyboardBuilder(); kb.button(text="شفاف", callback_data="simple:bg:transparent"); kb.button(text="پیش‌فرض", callback_data="simple:bg:default"); kb.button(text="ارسال عکس", callback_data="simple:bg:photo_prompt"); kb.adjust(3); return kb.as_markup()
def after_preview_kb(prefix: str):
    kb = InlineKeyboardBuilder(); kb.button(text="تایید", callback_data=f"{prefix}:confirm"); kb.button(text="ویرایش", callback_data=f"{prefix}:edit"); kb.button(text="بازگشت", callback_data="menu:home"); kb.adjust(2, 1); return kb.as_markup()
def rate_kb():
    kb = InlineKeyboardBuilder(); kb.button(text="بله", callback_data="rate:yes"); kb.button(text="خیر", callback_data="rate:no"); kb.button(text="ساخت پک جدید", callback_data="pack:start_creation"); kb.adjust(2, 1); return kb.as_markup()
def pack_selection_kb(uid: int, mode: str):
    kb = InlineKeyboardBuilder(); current_pack = get_current_pack(uid)
    if current_pack: kb.button(text=f"📦 {current_pack['name']} (فعلی)", callback_data=f"pack:select:{current_pack['short_name']}:{mode}")
    for pack in get_user_packs(uid):
        if not current_pack or pack["short_name"] != current_pack["short_name"]: kb.button(text=f"📦 {pack['name']}", callback_data=f"pack:select:{pack['short_name']}:{mode}")
    kb.button(text="➕ ساخت پک جدید", callback_data=f"pack:new:{mode}"); kb.adjust(1); return kb.as_markup()
def ai_type_kb():
    kb = InlineKeyboardBuilder(); kb.button(text="استیکر تصویری", callback_data="ai:type:image"); kb.button(text="استیکر ویدیویی", callback_data="ai:type:video"); kb.adjust(2); return kb.as_markup()
def ai_image_source_kb():
    kb = InlineKeyboardBuilder(); kb.button(text="متن بنویس", callback_data="ai:source:text"); kb.button(text="عکس بفرست", callback_data="ai:source:photo"); kb.adjust(2); return kb.as_markup()
def ai_vpos_kb():
    kb = InlineKeyboardBuilder(); kb.button(text="بالا", callback_data="ai:vpos:top"); kb.button(text="وسط", callback_data="ai:vpos:center"); kb.button(text="پایین", callback_data="ai:vpos:bottom"); kb.adjust(3); return kb.as_markup()
def ai_hpos_kb():
    kb = InlineKeyboardBuilder(); kb.button(text="چپ", callback_data="ai:hpos:left"); kb.button(text="وسط", callback_data="ai:hpos:center"); kb.button(text="راست", callback_data="ai:hpos:right"); kb.adjust(3); return kb.as_markup()
def admin_panel_kb():
    kb = InlineKeyboardBuilder(); kb.button(text="ارسال پیام همگانی", callback_data="admin:broadcast"); kb.button(text="ارسال به کاربر خاص", callback_data="admin:dm_prompt"); kb.button(text="تغییر سهمیه کاربر", callback_data="admin:quota_prompt"); kb.adjust(1); return kb.as_markup()

# --- Router ---
router = Router()

# --- Exports for handlers.py ---
__all__ = [
    "router", "SESSIONS", "USERS", "ADMIN_ID", "SUPPORT_USERNAME", "FORBIDDEN_WORDS",
    "user", "sess", "reset_mode", "_quota_left", "_seconds_to_reset", "_fmt_eta",
    "get_user_packs", "add_user_pack", "set_current_pack", "get_current_pack", "is_valid_pack_name", "check_pack_exists",
    "render_image", "is_ffmpeg_installed", "process_video_to_webm",
    "require_channel_membership", "check_channel_membership",
    "main_menu_kb", "back_to_menu_kb", "simple_bg_kb", "after_preview_kb", "rate_kb", "pack_selection_kb",
    "ai_type_kb", "ai_image_source_kb", "ai_vpos_kb", "ai_hpos_kb", "admin_panel_kb",
]
