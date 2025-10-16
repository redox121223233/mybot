import asyncio
import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import subprocess

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, BotCommand, BufferedInputFile, InputSticker
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# =============== پیکربندی ===============
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در محیط تنظیم کنید.")

CHANNEL_USERNAME = "@redoxbot_sticker"
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919

MAINTENANCE = False
DAILY_LIMIT = 5
BOT_USERNAME = ""

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
    if day_start is None or day_start < today:
        u["day_start"] = today
        u["ai_used"] = 0

def _quota_left(u: Dict[str, Any], is_admin: bool) -> int:
    if is_admin:
        return 999999
    _reset_daily_if_needed(u)
    # ابتدا سهمیه سفارشی کاربر را چک می‌کند
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
        USERS[uid] = {"ai_used": 0, "vote": None, "day_start": _today_start_ts(), "pack": None}
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
            "admin": {} # برای حالت‌های ادمین
        }
    return SESSIONS[uid]

def reset_mode(uid: int):
    """این تابع حالت کاربر را ریست می‌کند و اطلاعات او را از حافظه پاک می‌کند."""
    s = sess(uid)
    s["mode"] = "menu"
    s["ai"] = {}
    s["simple"] = {}
    s["await_feedback"] = False
    s["last_sticker"] = None
    s["last_video_sticker"] = None
    s["pack_wizard"] = {}
    s["admin"] = {} # حالت ادمین هم ریست می‌شود
    # پاک کردن اطلاعات کاربر برای ریست سهمیه
    if uid in USERS:
        del USERS[uid]

# ============ داده‌ها و NLU ساده ============
DEFAULT_PALETTE = [
    ("سفید", "#FFFFFF"), ("مشکی", "#000000"), ("قرمز", "#F43F5E"), ("آبی", "#3B82F6"),
    ("سبز", "#22C55E"), ("زرد", "#EAB308"), ("بنفش", "#8B5CF6"), ("نارنجی", "#F97316"),
]
NAME_TO_HEX = {name: hx for name, hx in DEFAULT_PALETTE}
POS_WORDS = {"بالا": "top", "وسط": "center", "میانه": "center", "پایین": "bottom"}
SIZE_WORDS = {"ریز": "small", "کوچک": "small", "متوسط": "medium", "بزرگ": "large", "درشت": "large"}

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
    """تشخیص زبان متن (فارسی یا انگلیسی)"""
    if not text:
        return "english"
    
    persian_pattern = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
    return "persian" if persian_pattern.search(text) else "english"

def resolve_font_path(font_key: Optional[str], text: str = "") -> str:
    """انتخاب فونت مناسب بر اساس زبان متن"""
    if font_key and font_key in _LOCAL_FONTS:
        return _LOCAL_FONTS[font_key]
    
    if text:
        lang = _detect_language(text)
        if lang == "persian":
            for font_name in PERSIAN_FONTS:
                if font_name in _LOCAL_FONTS:
                    return _LOCAL_FONTS[font_name]
        else:
            for font_name in ENGLISH_FONTS:
                if font_name in _LOCAL_FONTS:
                    return _LOCAL_FONTS[font_name]
    
    return next(iter(_LOCAL_FONTS.values()), "")

# ============ رندر تصویر/استیکر (اصلاح شده) ============
CANVAS = (512, 512)

def _prepare_text(text: str) -> str:
    """آماده‌سازی متن فارسی برای نمایش صحیح"""
    if not text:
        return ""
    
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    
    return bidi_text

def is_persian(text):
    """بررسی اینکه آیا متن فارسی است یا نه"""
    if not text:
        return False
    persian_pattern = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
    return bool(persian_pattern.search(text))

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    """تبدیل hex color به RGBA"""
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3:
        r, g, b = [int(c * 2, 16) for c in hx]
    else:
        r = int(hx[0:2], 16)
        g = int(hx[2:4], 16)
        b = int(hx[4:6], 16)
    return (r, g, b, 255)

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    """تنظیم اندازه فونت برای متناسب شدن در فضا"""
    size = base
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        if tw <= max_w and th <= max_h:
            return size
        
        size -= 1
    
    return max(size, 12)

def _make_default_bg(size=(512, 512)) -> Image.Image:
    """ایجاد پس‌زمینه پیش‌فرض با گرادیانت"""
    w, h = size
    img = Image.new("RGBA", size, (20, 20, 35, 255))
    top = (56, 189, 248)
    bottom = (99, 102, 241)
    dr = ImageDraw.Draw(img)
    
    for y in range(h):
        t = y / (h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        dr.line([(0, y), (w, y)], fill=(r, g, b, 255))
    
    return img.filter(ImageFilter.GaussianBlur(0.5))

def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str, 
                bg_mode: str = "transparent", bg_photo: Optional[bytes] = None, as_webp: bool = False) -> bytes:
    """رندر تصویر استیکر با موقعیت‌دهی کامل"""
    W, H = CANVAS
    
    if bg_photo:
        try:
            img = Image.open(BytesIO(bg_photo)).convert("RGBA").resize((W, H))
        except Exception:
            img = _make_default_bg((W, H)) if bg_mode == "default" else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    else:
        img = _make_default_bg((W, H)) if bg_mode == "default" else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    
    draw = ImageDraw.Draw(img)
    color = _parse_hex(color_hex)
    padding = 40
    box_w, box_h = W - 2 * padding, H - 2 * padding
    
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)
    
    font_path = resolve_font_path(font_key, text)
    txt = _prepare_text(text)
    
    final_size = fit_font_size(draw, txt, font_path, base_size, box_w, box_h)
    
    try:
        font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), txt, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # موقعیت‌دهی عمودی
    if v_pos == "top":
        y = padding
    elif v_pos == "bottom":
        y = H - padding - text_height
    else:  # center
        y = (H - text_height) / 2

    # موقعیت‌دهی افقی
    if h_pos == "left":
        x = padding
    elif h_pos == "right":
        x = W - padding
    else:  # center
        x = W / 2
    
    # رندر متن
    draw.text(
        (x, y),
        txt,
        font=font,
        fill=color,
        anchor="mm", # anchor را به mm (middle-middle) تغییر دادیم تا محاسبات درست باشد
        stroke_width=2,
        stroke_fill=(0, 0, 0, 220)
    )
    
    buf = BytesIO()
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

# ============ بررسی نصب بودن FFmpeg و پردازش ویدیو ============
def is_ffmpeg_installed() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

async def process_video_to_webm(video_bytes: bytes) -> Optional[bytes]:
    """Converts video bytes to webm format using FFmpeg."""
    if not is_ffmpeg_installed():
        return None
    try:
        process = subprocess.Popen(
            ['ffmpeg', '-i', '-', '-f', 'webm', '-c:v', 'libvpx-vp9', '-b:v', '1M', '-crf', '30', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=video_bytes)
        if process.returncode != 0:
            print(f"FFmpeg error: {stderr.decode()}")
            return None
        return stdout
    except Exception as e:
        print(f"Error during video processing: {e}")
        return None

# ============ کیبوردهای شیشه‌ای ============
def main_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر ساده 🎄", callback_data="menu:simple")
    kb.button(text="استیکر هوش مصنوعی 🤖", callback_data="menu:ai")
    kb.button(text="سهمیه امروز ⏳", callback_data="menu:quota")
    kb.button(text="راهنما ℹ️", callback_data="menu:help")
    kb.button(text="پشتیبانی 🛟", callback_data="menu:support")
    if is_admin:
        kb.button(text="پنل ادمین 🛠", callback_data="menu:admin")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

def back_to_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="بازگشت به منو ↩️", callback_data="menu:home")
    if is_admin:
        kb.button(text="پنل ادمین 🛠", callback_data="menu:admin")
    kb.adjust(1, 1)
    return kb.as_markup()

def simple_bg_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="شفاف ♻️", callback_data="simple:bg:transparent")
    kb.button(text="پیش‌فرض 🎨", callback_data="simple:bg:default")
    kb.button(text="ارسال عکس 🖼️", callback_data="simple:bg:photo_prompt")
    kb.adjust(3)
    return kb.as_markup()

def after_preview_kb(prefix: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="تایید ✅", callback_data=f"{prefix}:confirm")
    kb.button(text="ویرایش ✏️", callback_data=f"{prefix}:edit")
    kb.button(text="بازگشت ↩️", callback_data="menu:home")
    kb.adjust(2, 1)
    return kb.as_markup()

def rate_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="بله ✅", callback_data="rate:yes")
    kb.button(text="خیر ❌", callback_data="rate:no")
    kb.button(text="ساخت پک جدید 📦", callback_data="pack:start_creation")
    kb.adjust(2, 1)
    return kb.as_markup()

def pack_name_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="تایید و ساخت ✅", callback_data="pack:create")
    kb.button(text="انصراف ❌", callback_data="pack:cancel")
    kb.adjust(2)
    return kb.as_markup()

def ai_type_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر تصویری 🖼️", callback_data="ai:type:image")
    kb.button(text="استیکر ویدیویی 🎬", callback_data="ai:type:video")
    kb.adjust(2)
    return kb.as_markup()

def ai_image_source_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="متن بنویس 📝", callback_data="ai:source:text")
    kb.button(text="عکس بفرست 🖼️", callback_data="ai:source:photo")
    kb.adjust(2)
    return kb.as_markup()

def ai_vpos_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="بالا ⬆️", callback_data="ai:vpos:top")
    kb.button(text="وسط ⚪️", callback_data="ai:vpos:center")
    kb.button(text="پایین ⬇️", callback_data="ai:vpos:bottom")
    kb.adjust(3)
    return kb.as_markup()

def ai_hpos_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="چپ ⬅️", callback_data="ai:hpos:left")
    kb.button(text="وسط ⚪️", callback_data="ai:hpos:center")
    kb.button(text="راست ➡️", callback_data="ai:hpos:right")
    kb.adjust(3)
    return kb.as_markup()

def admin_panel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="ارسال پیام همگانی 📢", callback_data="admin:broadcast")
    kb.button(text="ارسال به کاربر خاص 👤", callback_data="admin:dm_prompt")
    kb.button(text="تغییر سهمیه کاربر ⚙️", callback_data="admin:quota_prompt")
    kb.adjust(1)
    return kb.as_markup()

# ============ ربات و روتر ============
router = Router()

@router.message(CommandStart())
async def on_start(message: Message):
    reset_mode(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "سلام! خوش آمدید 🎉\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=main_menu_kb(is_admin)
    )

@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery):
    reset_mode(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    await cb.message.answer(
        "منوی اصلی:",
        reply_markup=main_menu_kb(is_admin)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:help")
async def on_help(cb: CallbackQuery):
    help_text = (
        "راهنما ℹ️\n\n"
        "• استیکر ساده 🎄: متن بدون تنظیمات پیشرفته (موقعیت وسط)\n"
        "• استیکر هوش مصنوعی 🤖: تنظیمات پیشرفته شامل موقعیت، رنگ، فونت و اندازه\n"
        "• سهمیه امروز ⏳: مشاهده محدودیت استفاده از هوش مصنوعی\n"
        "• پشتیبانی 🛟: ارتباط با پشتیبانی\n\n"
        "برای ساخت استیکر کافیه متن مورد نظرت رو ارسال کنی!"
    )
    await cb.message.answer(help_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:support")
async def on_support(cb: CallbackQuery):
    await cb.message.answer(
        f"پشتیبانی: {SUPPORT_USERNAME}",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:quota")
async def on_quota(cb: CallbackQuery):
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    quota_txt = "نامحدود" if is_admin else f"{left} از {u.get('daily_limit', DAILY_LIMIT)}"
    await cb.message.answer(
        f"سهمیه امروز: {quota_txt}",
        reply_markup=back_to_menu_kb(is_admin)
    )
    await cb.answer()

# ----- پنل ادمین -----
@router.callback_query(F.data == "menu:admin")
async def on_admin_panel(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("شما دسترسی به این بخش را ندارید.", show_alert=True)
        return
    
    await cb.message.answer("پنل مدیریت ادمین:", reply_markup=admin_panel_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:broadcast")
async def on_admin_broadcast(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    sess(cb.from_user.id)["admin"]["mode"] = "awaiting_broadcast"
    await cb.message.answer("پیامی که می‌خواهید برای همه ارسال شود را بفرستید (متن، عکس یا ویدیو):")
    await cb.answer()

@router.callback_query(F.data == "admin:dm_prompt")
async def on_admin_dm_prompt(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    sess(cb.from_user.id)["admin"]["mode"] = "awaiting_dm_id"
    await cb.message.answer("آیدی عددی تلگرام کاربر مورد نظر را ارسال کنید:")
    await cb.answer()

@router.callback_query(F.data == "admin:quota_prompt")
async def on_admin_quota_prompt(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    sess(cb.from_user.id)["admin"]["mode"] = "awaiting_quota_change"
    await cb.message.answer("برای تغییر سهمیه، فرمت زیر را ارسال کنید:\n`user_id:new_quota`\n\nمثال: `123456789:10`")
    await cb.answer()

# ----- استیکر ساده -----
@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery):
    s = sess(cb.from_user.id)
    s["mode"] = "simple"
    s["simple"] =
