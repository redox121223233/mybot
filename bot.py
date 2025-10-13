import asyncio
import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import tempfile
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
    return max(0, DAILY_LIMIT - int(u.get("ai_used", 0)))

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
            "last_video_sticker": None
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

# ============ رندر تصویر/استیکر ============
CANVAS = (512, 512)

def _prepare_text(text: str) -> str:
    """آماده‌سازی متن فارسی برای نمایش صحیح"""
    if not text:
        return ""
    
    # استفاده از arabic_reshaper برای اتصال حروف فارسی
    reshaped_text = arabic_reshaper.reshape(text)
    
    # استفاده از bidi برای ترتیب صحیح RTL
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

def wrap_text_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """پیچیدن متن در عرض مشخص"""
    words = text.split()
    if not words:
        return [text]
    
    lines: List[str] = []
    cur = ""
    
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    
    if cur:
        lines.append(cur)
    
    return lines

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    """تنظیم اندازه فونت برای متناسب شدن در فضا"""
    size = base
    while size > 12:
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        
        lines = wrap_text_to_width(draw, text, font, max_w)
        bbox = draw.multiline_textbbox((0, 0), "\n".join(lines), font=font, spacing=4, align="center")
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

def render_image(text: str, position: str, font_key: str, color_hex: str, size_key: str, 
                bg_mode: str = "transparent", bg_photo: Optional[bytes] = None, as_webp: bool = False) -> bytes:
    """رندر تصویر استیکر با متن فارسی"""
    W, H = CANVAS
    
    if bg_mode == "default":
        img = _make_default_bg((W, H))
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    
    draw = ImageDraw.Draw(img)
    color = _parse_hex(color_hex)
    padding = 28
    box_w, box_h = W - 2 * padding, H - 2 * padding
    
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)
    
    font_path = resolve_font_path(font_key, text)
    try:
        font = ImageFont.truetype(font_path, size=base_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    txt = _prepare_text(text)
    if not font_path:
        font_path = resolve_font_path("Default")
    
    final_size = fit_font_size(draw, txt, font_path, base_size, box_w, box_h)
    try:
        font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    lines = wrap_text_to_width(draw, txt, font, box_w)
    wrapped = "\n".join(lines)
    
    # تنظیم موقعیت متن بر اساس زبان
    is_fa = is_persian(text)
    
    if is_fa:
        align = "right"
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6, align="right")
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        if position == "top":
            x, y = W - padding, padding
            anchor = "rt"
        elif position == "bottom":
            x, y = W - padding, H - padding
            anchor = "rb"
        else:
            x, y = W - padding, H / 2
            anchor = "rm"
    else:
        align = "left"
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6, align="left")
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        if position == "top":
            x, y = padding, padding
            anchor = "lt"
        elif position == "bottom":
            x, y = padding, H - padding
            anchor = "lb"
        else:
            x, y = W / 2, H / 2
            anchor = "mm"
            align = "center"
    
    # رندر متن
    draw.text(
        (x, y),
        wrapped,
        font=font,
        fill=color,
        anchor=anchor,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 220)
    )
    
    buf = BytesIO()
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

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
    kb.adjust(2)
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
    kb.adjust(2)
    return kb.as_markup()

def add_to_pack_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="افزودن به پک 📦", callback_data="pack:add")
    kb.button(text="نه، لازم نیست", callback_data="pack:skip")
    kb.adjust(2)
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
        "• استیکر ساده 🎄: متن بدون تنظیمات پیشرفته\n"
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
    quota_txt = "نامحدود" if is_admin else f"{left} از {DAILY_LIMIT}"
    await cb.message.answer(
        f"سهمیه امروز: {quota_txt}",
        reply_markup=back_to_menu_kb(is_admin)
    )
    await cb.answer()

# ----- استیکر ساده -----
@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery):
    s = sess(cb.from_user.id)
    s["mode"] = "simple"
    s["simple"] = {"text": None, "bg_mode": "transparent"}
    await cb.message.answer(
        "متن استیکر ساده رو بفرست:",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "simple:bg:transparent")
async def on_simple_transparent(cb: CallbackQuery):
    s = sess(cb.from_user.id)["simple"]
    s["bg_mode"] = "transparent"
    if s.get("text"):
        img = render_image(
            text=s["text"], 
            position="center", 
            font_key="Default", 
            color_hex="#FFFFFF",
            size_key="medium", 
            bg_mode="transparent", 
            as_webp=False
        )
        file_obj = BufferedInputFile(img, filename="preview.png")
        await cb.message.answer_photo(
            file_obj, 
            caption="پیش‌نمایش آماده است",
            reply_markup=after_preview_kb("simple")
        )
    await cb.answer()

@router.callback_query(F.data == "simple:bg:default")
async def on_simple_default(cb: CallbackQuery):
    s = sess(cb.from_user.id)["simple"]
    s["bg_mode"] = "default"
    if s.get("text"):
        img = render_image(
            text=s["text"], 
            position="center", 
            font_key="Default", 
            color_hex="#FFFFFF",
            size_key="medium", 
            bg_mode="default", 
            as_webp=False
        )
        file_obj = BufferedInputFile(img, filename="preview.png")
        await cb.message.answer_photo(
            file_obj, 
            caption="پیش‌نمایش آماده است",
            reply_markup=after_preview_kb("simple")
        )
    await cb.answer()

@router.callback_query(F.data == "simple:confirm")
async def on_simple_confirm(cb: CallbackQuery):
    s = sess(cb.from_user.id)["simple"]
    img = render_image(
        text=s["text"] or "سلام",
        position="center",
        font_key="Default",
        color_hex="#FFFFFF",
        size_key="medium",
        bg_mode=s.get("bg_mode") or "transparent",
        as_webp=True
    )
    sess(cb.from_user.id)["last_sticker"] = img
    await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
    await cb.message.answer(
        "از این استیکر راضی بودی؟",
        reply_markup=rate_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "simple:edit")
async def on_simple_edit(cb: CallbackQuery):
    await cb.message.answer(
        "پس‌زمینه رو انتخاب کن:",
        reply_markup=simple_bg_kb()
    )
    await cb.answer()

# ----- استیکر هوش مصنوعی -----
@router.callback_query(F.data == "menu:ai")
async def on_ai(cb: CallbackQuery):
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    
    if left <= 0 and not is_admin:
        await cb.message.answer(
            f"سهمیه امروز تمام شد! فردا دوباره امتحان کن",
            reply_markup=back_to_menu_kb(is_admin)
        )
        await cb.answer()
        return
    
    s = sess(cb.from_user.id)
    s["mode"] = "ai"
    s["ai"] = {
        "text": None, "position": "center", "font": "Default",
        "color": "#FFFFFF", "size": "large"
    }
    
    kb = InlineKeyboardBuilder()
    kb.button(text="بالا ⬆️", callback_data="ai:pos:top")
    kb.button(text="وسط ⚪️", callback_data="ai:pos:center")
    kb.button(text="پایین ⬇️", callback_data="ai:pos:bottom")
    kb.adjust(3)
    
    await cb.message.answer(
        f"متن استیکر هوش مصنوعی رو بفرست:\n(سهمیه: {'نامحدود' if is_admin else f'{left} از {DAILY_LIMIT}'})",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:pos:")))
async def on_ai_pos(cb: CallbackQuery):
    pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["position"] = pos
    
    kb = InlineKeyboardBuilder()
    for name, hx in DEFAULT_PALETTE:
        kb.button(text=name, callback_data=f"ai:color:{hx}")
    kb.adjust(4)
    
    await cb.message.answer("رنگ متن:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:color:")))
async def on_ai_color(cb: CallbackQuery):
    color = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["color"] = color
    
    kb = InlineKeyboardBuilder()
    for label, val in [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]:
        kb.button(text=label, callback_data=f"ai:size:{val}")
    kb.adjust(3)
    
    await cb.message.answer("اندازه فونت:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:size:")))
async def on_ai_size(cb: CallbackQuery):
    size = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["size"] = size
    
    img = render_image(
        text=sess(cb.from_user.id)["ai"].get("text") or "نمونه",
        position=sess(cb.from_user.id)["ai"]["position"],
        font_key="Default",
        color_hex=sess(cb.from_user.id)["ai"]["color"],
        size_key=size,
        bg_mode="transparent",
        as_webp=False
    )
    
    file_obj = BufferedInputFile(img, filename="preview.png")
    await cb.message.answer_photo(
        file_obj,
        caption="پیش‌نمایش آماده است",
        reply_markup=after_preview_kb("ai")
    )
    await cb.answer()

@router.callback_query(F.data == "ai:confirm")
async def on_ai_confirm(cb: CallbackQuery):
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    
    if left <= 0 and not is_admin:
        await cb.answer("سهمیه تمام شد!", show_alert=True)
        return
    
    ai_data = sess(cb.from_user.id)["ai"]
    img = render_image(
        text=ai_data.get("text") or "سلام",
        position=ai_data["position"],
        font_key="Default",
        color_hex=ai_data["color"],
        size_key=ai_data["size"],
        bg_mode="transparent",
        as_webp=True
    )
    
    sess(cb.from_user.id)["last_sticker"] = img
    if not is_admin:
        u["ai_used"] = int(u.get("ai_used", 0)) + 1
    
    await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
    await cb.message.answer(
        "از این استیکر راضی بودی؟",
        reply_markup=rate_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "ai:edit")
async def on_ai_edit(cb: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="بالا ⬆️", callback_data="ai:pos:top")
    kb.button(text="وسط ⚪️", callback_data="ai:pos:center")
    kb.button(text="پایین ⬇️", callback_data="ai:pos:bottom")
    kb.adjust(3)
    
    await cb.message.answer(
        "موقعیت متن:",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

# ----- بازخورد و افزودن به پک -----
@router.callback_query(F.data == "rate:yes")
async def on_rate_yes(cb: CallbackQuery):
    await cb.message.answer(
        "عالیه! می‌خوای به پک اضافه کنیم؟",
        reply_markup=add_to_pack_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "rate:no")
async def on_rate_no(cb: CallbackQuery):
    sess(cb.from_user.id)["await_feedback"] = True
    await cb.message.answer(
        "چه چیزی رو دوست نداشتی؟ لطفاً نظرت رو بنویس:"
    )
    await cb.answer()

@router.callback_query(F.data == "pack:skip")
async def on_pack_skip(cb: CallbackQuery):
    await cb.message.answer(
        "باشه، اضافه نکردم. هر وقت خواستی از منو می‌تونی دوباره استیکر بسازی.",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "pack:add")
async def on_pack_add(cb: CallbackQuery):
    await cb.message.answer(
        "✅ استیکر ساخته شد!\n"
        "برای ذخیره، روی استیکر کلیک کن و 'Add to Favorites' رو بزن.",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

# ----- پردازش پیام‌ها -----
@router.message()
async def on_message(message: Message):
    uid = message.from_user.id
    
    # بررسی بازخورد
    s = sess(uid)
    if s.get("await_feedback") and message.text:
        s["await_feedback"] = False
        await message.answer(
            "ممنون از بازخوردت 🙏",
            reply_markup=back_to_menu_kb(uid == ADMIN_ID)
        )
        return
    
    # پردازش بر اساس حالت
    mode = s.get("mode", "menu")
    
    if mode == "simple":
        s["simple"]["text"] = message.text.strip()
        await message.answer(
            "پس‌زمینه رو انتخاب کن:",
            reply_markup=simple_bg_kb()
        )
    elif mode == "ai":
        u = user(uid)
        is_admin = (uid == ADMIN_ID)
        left = _quota_left(u, is_admin)
        
        if left <= 0 and not is_admin:
            await message.answer(
                f"سهمیه امروز تمام شد! فردا دوباره امتحان کن",
                reply_markup=back_to_menu_kb(is_admin)
            )
            return
        
        s["ai"]["text"] = message.text.strip()
        
        kb = InlineKeyboardBuilder()
        kb.button(text="بالا ⬆️", callback_data="ai:pos:top")
        kb.button(text="وسط ⚪️", callback_data="ai:pos:center")
        kb.button(text="پایین ⬇️", callback_data="ai:pos:bottom")
        kb.adjust(3)
        
        await message.answer(
            "موقعیت متن:",
            reply_markup=kb.as_markup()
        )
    else:
        # حالت پیش‌فرض
        is_admin = (uid == ADMIN_ID)
        await message.answer(
            "از منوی زیر انتخاب کن:",
            reply_markup=main_menu_kb(is_admin)
        )

# برای سازگاری با محیط سرورلس
__all__ = ['router']