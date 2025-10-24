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

# ============ داده‌ها و NLU ساده ============
DEFAULT_PALETTE = [
    ("سفید", "#FFFFFF"), ("مشکی", "#000000"), ("قرمز", "#F43F5E"), ("آبی", "#3B82F6"),
    ("سبز", "#22C55E"), ("زرد", "#EAB308"), ("بنفش", "#8B5CF6"), ("نارنجی", "#F97316"),
]
NAME_TO_HEX = {name: hx for name, hx in DEFAULT_PALETTE}
POS_WORDS = {"بالا": "top", "وسط": "center", "میانه": "center", "پایین": "bottom"}
SIZE_WORDS = {"ریز": "small", "متوسط": "medium", "بزرگ": "large", "درشت": "large"}

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

def _detect_language(text: str) -> str:
    if not text:
        return "english"
    persian_pattern = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
    return "persian" if persian_pattern.search(text) else "english"

def resolve_font_path(font_key: Optional[str], text: str = "") -> str:
    if font_key and font_key in _LOCAL_FONTS:
        return _LOCAL_FONTS[font_key]
    if text:
        lang = _detect_language(text)
        font_list = PERSIAN_FONTS if lang == "persian" else ENGLISH_FONTS
        for font_name in font_list:
            if font_name in _LOCAL_FONTS:
                return _LOCAL_FONTS[font_name]
    return next(iter(_LOCAL_FONTS.values()), "")

# ============ رندر تصویر/استیکر ============
CANVAS = (512, 512)

def _prepare_text(text: str) -> str:
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3:
        r, g, b = [int(c * 2, 16) for c in hx]
    else:
        r = int(hx[0:2], 16)
        g = int(hx[2:4], 16)
        b = int(hx[4:6], 16)
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
        if tw <= max_w and th <= max_h:
            return size
        size -= 1
    return max(size, 12)

def _make_default_bg(size=(512, 512)) -> Image.Image:
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

    if v_pos == "top":
        y = padding
    elif v_pos == "bottom":
        y = H - padding - text_height
    else:
        y = (H - text_height) / 2

    if h_pos == "left":
        x = padding
    elif h_pos == "right":
        x = W - padding - text_width
    else:
        x = W / 2

    draw.text(
        (x, y),
        txt,
        font=font,
        fill=color,
        anchor="mm" if h_pos == "center" else "lm",
        stroke_width=2,
        stroke_fill=(0, 0, 0, 220)
    )

    buf = BytesIO()
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

# ============ FFmpeg ============
def is_ffmpeg_installed() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

async def process_video_to_webm(video_bytes: bytes) -> Optional[bytes]:
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

# ============ توابع کمکی پک ============
async def check_pack_exists(bot: Bot, short_name: str) -> bool:
    try:
        await bot.get_sticker_set(name=short_name)
        return True
    except TelegramBadRequest as e:
        if "STICKERSET_INVALID" in e.message or "invalid sticker set name" in e.message.lower():
            return False
        raise

def is_valid_pack_name(name: str) -> bool:
    if not (1 <= len(name) <= 50):
        return False
    if not name[0].isalpha() or not name[0].islower():
        return False
    if name.endswith('_'):
        return False
    if '__' in name:
        return False
    for char in name:
        if not (char.islower() or char.isdigit() or char == '_'):
            return False
    return True

# ============ دکوراتور بررسی عضویت (راه حل اصلی مشکل) ============
def check_membership_decorator(handler):
    async def wrapper(message_or_callback, bot: Bot, *args, **kwargs):
        try:
            member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=message_or_callback.from_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                kb = InlineKeyboardBuilder()
                kb.button(text="عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
                kb.button(text="بررسی عضویت", callback_data="check_membership")
                kb.adjust(1)
                
                if isinstance(message_or_callback, Message):
                    await message_or_callback.answer(
                        f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.\n\nپس از عضویت، روی دکمه «بررسی عضویت» کلیک کنید.",
                        reply_markup=kb.as_markup()
                    )
                elif isinstance(message_or_callback, CallbackQuery):
                    await message_or_callback.message.answer(
                        f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.\n\nپس از عضویت، روی دکمه «بررسی عضویت» کلیک کنید.",
                        reply_markup=kb.as_markup()
                    )
                    await message_or_callback.answer()
                return
        except Exception as e:
            print(f"Error checking channel membership: {e}")
        
        return await handler(message_or_callback, bot, *args, **kwargs)
    return wrapper

# ============ کیبوردها ============
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

def simple_bg_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="شفاف", callback_data="simple:bg:transparent")
    kb.button(text="پیش‌فرض", callback_data="simple:bg:default")
    kb.button(text="ارسال عکس", callback_data="simple:bg:photo_prompt")
    kb.adjust(3)
    return kb.as_markup()

def after_preview_kb(prefix: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="تایید", callback_data=f"{prefix}:confirm")
    kb.button(text="ویرایش", callback_data=f"{prefix}:edit")
    kb.button(text="بازگشت", callback_data="menu:home")
    kb.adjust(2, 1)
    return kb.as_markup()

def rate_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="بله", callback_data="rate:yes")
    kb.button(text="خیر", callback_data="rate:no")
    kb.button(text="ساخت پک جدید", callback_data="pack:start_creation")
    kb.adjust(2, 1)
    return kb.as_markup()

def pack_selection_kb(uid: int, mode: str):
    kb = InlineKeyboardBuilder()
    user_packs = get_user_packs(uid)
    current_pack = get_current_pack(uid)
    if current_pack:
        kb.button(text=f"📦 {current_pack['name']} (فعلی)", callback_data=f"pack:select:{current_pack['short_name']}")
    for pack in user_packs:
        if current_pack and pack["short_name"] == current_pack["short_name"]:
            continue
        kb.button(text=f"📦 {pack['name']}", callback_data=f"pack:select:{pack['short_name']}")
    kb.button(text="➕ ساخت پک جدید", callback_data=f"pack:new:{mode}")
    kb.adjust(1)
    return kb.as_markup()

def ai_type_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر تصویری", callback_data="ai:type:image")
    kb.button(text="استیکر ویدیویی", callback_data="ai:type:video")
    kb.adjust(2)
    return kb.as_markup()

def ai_image_source_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="متن بنویس", callback_data="ai:source:text")
    kb.button(text="عکس بفرست", callback_data="ai:source:photo")
    kb.adjust(2)
    return kb.as_markup()

def ai_vpos_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="بالا", callback_data="ai:vpos:top")
    kb.button(text="وسط", callback_data="ai:vpos:center")
    kb.button(text="پایین", callback_data="ai:vpos:bottom")
    kb.adjust(3)
    return kb.as_markup()

def ai_hpos_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="چپ", callback_data="ai:hpos:left")
    kb.button(text="وسط", callback_data="ai:hpos:center")
    kb.button(text="راست", callback_data="ai:hpos:right")
    kb.adjust(3)
    return kb.as_markup()

def admin_panel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="ارسال پیام همگانی", callback_data="admin:broadcast")
    kb.button(text="ارسال به کاربر خاص", callback_data="admin:dm_prompt")
    kb.button(text="تغییر سهمیه کاربر", callback_data="admin:quota_prompt")
    kb.adjust(1)
    return kb.as_markup()

# ============ روتر ============
router = Router()

@router.message(CommandStart())
@check_membership_decorator
async def on_start(message: Message, bot: Bot):
    reset_mode(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "سلام! خوش آمدید\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=main_menu_kb(is_admin)
    )

@router.callback_query(F.data == "check_membership")
async def on_check_membership(cb: CallbackQuery, bot: Bot):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=cb.from_user.id)
        if member.status in ["member", "administrator", "creator"]:
            await cb.message.answer(
                "عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.",
                reply_markup=main_menu_kb(cb.from_user.id == ADMIN_ID)
            )
        else:
            await cb.answer("شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
    except Exception as e:
        print(f"Error in check_membership callback: {e}")
        await cb.answer("خطایی در بررسی عضویت رخ داد. لطفا دوباره تلاش کنید.", show_alert=True)
    await cb.answer()

@router.callback_query(F.data == "menu:home")
@check_membership_decorator
async def on_home(cb: CallbackQuery, bot: Bot):
    reset_mode(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    await cb.message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
    await cb.answer()

@router.callback_query(F.data == "menu:admin")
@check_membership_decorator
async def on_admin_panel(cb: CallbackQuery, bot: Bot):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("شما دسترسی به این بخش را ندارید.", show_alert=True)
        return
    await cb.message.answer("پنل ادمین:", reply_markup=admin_panel_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:broadcast")
@check_membership_decorator
async def on_admin_broadcast(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "broadcast"
    await cb.message.answer("پیام همگانی خود را ارسال کنید. برای انصراف /cancel را بفرستید.")
    await cb.answer()

@router.callback_query(F.data == "admin:dm_prompt")
@check_membership_decorator
async def on_admin_dm_prompt(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "dm_get_user"
    await cb.message.answer("آیدی عددی کاربر مورد نظر را ارسال کنید. برای انصراف /cancel را بفرستید.")
    await cb.answer()

@router.callback_query(F.data == "admin:quota_prompt")
@check_membership_decorator
async def on_admin_quota_prompt(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "quota_get_user"
    await cb.message.answer("آیدی عددی کاربر مورد نظر را برای تغییر سهمیه ارسال کنید. برای انصراف /cancel را بفرستید.")
    await cb.answer()

@router.callback_query(F.data == "menu:help")
@check_membership_decorator
async def on_help(cb: CallbackQuery, bot: Bot):
    help_text = (
        "راهنما\n\n"
        "• استیکر ساده: ساخت استیکر با تنظیمات سریع\n"
        "• استیکر ساز پیشرفته: ساخت استیکر با تنظیمات پیشرفته\n"
        "• سهمیه امروز: محدودیت استفاده روزانه\n"
        "• پشتیبانی: ارتباط با ادمین"
    )
    await cb.message.answer(help_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:support")
@check_membership_decorator
async def on_support(cb: CallbackQuery, bot: Bot):
    await cb.message.answer(
        f"پشتیبانی: {SUPPORT_USERNAME}",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:quota")
@check_membership_decorator
async def on_quota(cb: CallbackQuery, bot: Bot):
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    quota_txt = "نامحدود" if is_admin else f"{left} از {u.get('daily_limit', DAILY_LIMIT)}"
    await cb.message.answer(
        f"سهمیه امروز: {quota_txt}",
        reply_markup=back_to_menu_kb(is_admin)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:simple")
@check_membership_decorator
async def on_simple(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)
    uid = cb.from_user.id
    user_packs = get_user_packs(uid)
    if user_packs:
        s["pack_wizard"] = {"mode": "simple"}
        await cb.message.answer(
            "می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟",
            reply_markup=pack_selection_kb(uid, "simple")
        )
    else:
        s["pack_wizard"] = {"step": "awaiting_name", "mode": "simple"}
        rules_text = (
            "نام پک را بنویس (مثال: my_stickers):\n\n"
            "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
            "• باید با حرف شروع شود\n"
            "• نباید با زیرخط تمام شود\n"
            "• نباید دو زیرخط پشت سر هم داشته باشد\n"
            "• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)"
        )
        await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:ai")
@check_membership_decorator
async def on_ai(cb: CallbackQuery, bot: Bot):
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    if left <= 0 and not is_admin:
        await cb.message.answer("سهمیه امروز تمام شد!", reply_markup=back_to_menu_kb(is_admin))
        await cb.answer()
        return
    s = sess(cb.from_user.id)
    uid = cb.from_user.id
    user_packs = get_user_packs(uid)
    if user_packs:
        s["pack_wizard"] = {"mode": "ai"}
        await cb.message.answer(
            "می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟",
            reply_markup=pack_selection_kb(uid, "ai")
        )
    else:
        s["pack_wizard"] = {"step": "awaiting_name", "mode": "ai"}
        rules_text = (
            "نام پک را بنویس (مثال: my_stickers):\n\n"
            "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
            "• باید با حرف شروع شود\n"
            "• نباید با زیرخط تمام شود\n"
            "• نباید دو زیرخط پشت سر هم داشته باشد\n"
            "• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)"
        )
        await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("pack:select:"))
@check_membership_decorator
async def on_pack_select(cb: CallbackQuery, bot: Bot):
    pack_short_name = cb.data.split(":")[-1]
    uid = cb.from_user.id
    s = sess(uid)
    selected_pack = None
    for pack in get_user_packs(uid):
        if pack["short_name"] == pack_short_name:
            selected_pack = pack
            break
    if selected_pack:
        set_current_pack(uid, pack_short_name)
        s["current_pack_short_name"] = pack_short_name
        s["current_pack_title"] = selected_pack["name"]
        s["pack_wizard"] = {}
        mode = s.get("pack_wizard", {}).get("mode", "simple")
        if mode == "simple":
            s["mode"] = "simple"
            s["simple"] = {"text": None, "bg_mode": "transparent", "bg_photo_bytes": None}
            await cb.message.answer(
                f"پک «{selected_pack['name']}» انتخاب شد.\n\nمتن استیکر ساده رو بفرست:",
                reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
            )
        elif mode == "ai":
            s["mode"] = "ai"
            s["ai"] = {
                "text": None, "v_pos": "center", "h_pos": "center", "font": "Default",
                "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None
            }
            await cb.message.answer(
                f"پک «{selected_pack['name']}» انتخاب شد.\n\nنوع استیکر پیشرفته را انتخاب کنید:",
                reply_markup=ai_type_kb()
            )
    await cb.answer()

@router.callback_query(F.data.startswith("pack:new:"))
@check_membership_decorator
async def on_pack_new(cb: CallbackQuery, bot: Bot):
    mode = cb.data.split(":")[-1]
    s = sess(cb.from_user.id)
    s["pack_wizard"] = {"step": "awaiting_name", "mode": mode}
    rules_text = (
        "برای ایجاد پک جدید، یک نام انگلیسی ارسال کنید.\n\n"
        "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
        "• حداکثر ۵۰ کاراکتر"
    )
    await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "pack:select_existing")
@check_membership_decorator
async def on_pack_select_existing(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)
    mode = s.get("pack_wizard", {}).get("mode", "simple")
    await cb.message.answer(
        "کدام پک را انتخاب می‌کنید؟",
        reply_markup=pack_selection_kb(cb.from_user.id, mode)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("simple:bg:"))
@check_membership_decorator
async def on_simple_bg(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)["simple"]
    mode = cb.data.split(":")[-1]
    if mode == "photo_prompt":
        s["awaiting_bg_photo"] = True
        await cb.message.answer("عکس مورد نظر برای پس‌زمینه را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    else:
        s["bg_mode"] = mode
        s["bg_photo_bytes"] = None
        if s.get("text"):
            img = render_image(
                text=s["text"], v_pos="center", h_pos="center", font_key="Default",
                color_hex="#FFFFFF", size_key="medium", bg_mode=mode,
                bg_photo=s.get("bg_photo_bytes"), as_webp=False
            )
            file_obj = BufferedInputFile(img, filename="preview.png")
            await cb.message.answer_photo(
                file_obj, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple")
            )
    await cb.answer()

@router.callback_query(F.data == "simple:confirm")
@check_membership_decorator
async def on_simple_confirm(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)
    simple_data = s["simple"]
    img = render_image(
        text=simple_data["text"] or "سلام", v_pos="center", h_pos="center", font_key="Default",
        color_hex="#FFFFFF", size_key="medium", bg_mode=simple_data.get("bg_mode") or "transparent",
        bg_photo=simple_data.get("bg_photo_bytes"), as_webp=True
    )
    s["last_sticker"] = img
    await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
    await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
    await cb.answer()

@router.callback_query(F.data == "simple:edit")
@check_membership_decorator
async def on_simple_edit(cb: CallbackQuery, bot: Bot):
    await cb.message.answer("پس‌زمینه رو انتخاب کن:", reply_markup=simple_bg_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ai:type:"))
@check_membership_decorator
async def on_ai_type(cb: CallbackQuery, bot: Bot):
    sticker_type = cb.data.split(":")[-1]
    s = sess(cb.from_user.id)
    s["ai"]["sticker_type"] = sticker_type
    if sticker_type == "image":
        await cb.message.answer("منبع استیکر تصویری را انتخاب کنید:", reply_markup=ai_image_source_kb())
    elif sticker_type == "video":
        if not is_ffmpeg_installed():
            await cb.message.answer("قابلیت ویدیو فعال نیست.", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        else:
            await cb.message.answer("یک فایل ویدیو ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "ai:source:text")
@check_membership_decorator
async def on_ai_source_text(cb: CallbackQuery, bot: Bot):
    await cb.message.answer("متن استیکر را بفرست:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "ai:source:photo")
@check_membership_decorator
async def on_ai_source_photo(cb: CallbackQuery, bot: Bot):
    sess(cb.from_user.id)["ai"]["awaiting_bg_photo"] = True
    await cb.message.answer("عکس را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("ai:vpos:"))
@check_membership_decorator
async def on_ai_vpos(cb: CallbackQuery, bot: Bot):
    v_pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["v_pos"] = v_pos
    await cb.message.answer("موقعیت افقی متن:", reply_markup=ai_hpos_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ai:hpos:"))
@check_membership_decorator
async def on_ai_hpos(cb: CallbackQuery, bot: Bot):
    h_pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["h_pos"] = h_pos
    kb = InlineKeyboardBuilder()
    for name, hx in DEFAULT_PALETTE:
        kb.button(text=name, callback_data=f"ai:color:{hx}")
    kb.adjust(4)
    await cb.message.answer("رنگ متن:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:color:")))
@check_membership_decorator
async def on_ai_color(cb: CallbackQuery, bot: Bot):
    color = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["color"] = color
    kb = InlineKeyboardBuilder()
    for label, val in [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]:
        kb.button(text=label, callback_data=f"ai:size:{val}")
    kb.adjust(3)
    await cb.message.answer("اندازه فونت:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:size:")))
@check_membership_decorator
async def on_ai_size(cb: CallbackQuery, bot: Bot):
    size = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["size"] = size
    ai_data = sess(cb.from_user.id)["ai"]
    img = render_image(
        text=ai_data.get("text") or "متن ساده", v_pos=ai_data["v_pos"], h_pos=ai_data["h_pos"],
        font_key="Default", color_hex=ai_data["color"], size_key=size, bg_mode="transparent",
        bg_photo=ai_data.get("bg_photo_bytes"), as_webp=False
    )
    file_obj = BufferedInputFile(img, filename="preview.png")
    await cb.message.answer_photo(
        file_obj, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("ai")
    )
    await cb.answer()

@router.callback_query(F.data == "ai:confirm")
@check_membership_decorator
async def on_ai_confirm(cb: CallbackQuery, bot: Bot):
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    if left <= 0 and not is_admin:
        await cb.answer("سهمیه تمام شد!", show_alert=True)
        return
    ai_data = sess(cb.from_user.id)["ai"]
    img = render_image(
        text=ai_data.get("text") or "سلام", v_pos=ai_data["v_pos"], h_pos=ai_data["h_pos"],
        font_key="Default", color_hex=ai_data["color"], size_key=ai_data["size"],
        bg_mode="transparent", bg_photo=ai_data.get("bg_photo_bytes"), as_webp=True
    )
    sess(cb.from_user.id)["last_sticker"] = img
    if not is_admin:
        u["ai_used"] = int(u.get("ai_used", 0)) + 1
    await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
    await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
    await cb.answer()

@router.callback_query(F.data == "ai:edit")
@check_membership_decorator
async def on_ai_edit(cb: CallbackQuery, bot: Bot):
    await cb.message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
    await cb.answer()

@router.callback_query(F.data == "rate:yes")
@check_membership_decorator
async def on_rate_yes(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)
    sticker_bytes = s.get("last_sticker")
    pack_short_name = s.get("current_pack_short_name")
    pack_title = s.get("current_pack_title")
    if not sticker_bytes or not pack_short_name:
        await cb.message.answer("خطایی در پیدا کردن پک یا استیکر رخ داد. لطفا دوباره تلاش کنید.", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()
        return
    if len(sticker_bytes) > 64 * 1024:
        await cb.message.answer("فایل استیکر خیلی بزرگ است. لطفا با متن کوتاه‌تر یا ساده‌تر دوباره تلاش کنید.", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()
        return
    await cb.message.answer("در حال افزودن استیکر به پک، لطفا چند لحظه صبر کنید...")
    await asyncio.sleep(1.5)
    try:
        sticker_to_add = InputSticker(
            sticker=BufferedInputFile(sticker_bytes, filename="sticker.webp"),
            emoji_list=["😂"]
        )
        await cb.bot.add_sticker_to_set(
            user_id=cb.from_user.id, name=pack_short_name, sticker=sticker_to_add
        )
        pack_link = f"https://t.me/addstickers/{pack_short_name}"
        await cb.message.answer(f"استیکر با موفقیت به پک «{pack_title}» اضافه شد.\n\n{pack_link}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    except TelegramBadRequest as e:
        await cb.message.answer(f"خطا در افزودن استیکر به پک: {e.message}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    except Exception as e:
        traceback.print_exc()
        await cb.message.answer(f"خطای غیرمنتظره‌ای رخ داد. لطفا به ادمین اطلاع دهید.\nخطا: {str(e)}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "rate:no")
@check_membership_decorator
async def on_rate_no(cb: CallbackQuery, bot: Bot):
    sess(cb.from_user.id)["await_feedback"] = True
    await cb.message.answer("چه چیزی رو دوست نداشتی؟")
    await cb.answer()

@router.callback_query(F.data == "pack:skip")
@check_membership_decorator
async def on_pack_skip(cb: CallbackQuery, bot: Bot):
    await cb.message.answer("باشه، اضافه نکردم.", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "pack:start_creation")
@check_membership_decorator
async def on_pack_start_creation(cb: CallbackQuery, bot: Bot):
    s = sess(cb.from_user.id)
    mode = s.get("pack_wizard", {}).get("mode", "simple")
    s["pack_wizard"] = {"step": "awaiting_name", "mode": mode}
    rules_text = (
        "برای ایجاد پک جدید، یک نام انگلیسی ارسال کنید.\n\n"
        "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
        "• حداکثر ۵۰ کاراکتر"
    )
    await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.message()
@check_membership_decorator
async def on_message(message: Message, bot: Bot):
    uid = message.from_user.id
    s = sess(uid)
    is_admin = (uid == ADMIN_ID)
    if is_admin and s["admin"].get("action"):
        action = s["admin"]["action"]
        if action == "broadcast":
            s["admin"]["action"] = None
            success_count = 0
            for user_id in USERS:
                try:
                    await message.bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
                    success_count += 1
                except Exception:
                    pass
            await message.answer(f"پیام همگانی با موفقیت به {success_count} کاربر ارسال شد.")
            return
        if action == "dm_get_user":
            if message.text and message.text.isdigit():
                target_uid = int(message.text)
                s["admin"]["target_uid"] = target_uid
                s["admin"]["action"] = "dm_get_text"
                await message.answer(f"پیام خود را برای ارسال به کاربر {target_uid} بنویسید:")
            else:
                await message.answer("آیدی عددی نامعتبر است. لطفا دوباره تلاش کنید.")
            return
        if action == "dm_get_text":
            target_uid = s["admin"].get("target_uid")
            s["admin"]["action"] = None
            try:
                await message.bot.copy_message(chat_id=target_uid, from_chat_id=message.chat.id, message_id=message.message_id)
                await message.answer(f"پیام به کاربر {target_uid} ارسال شد.")
            except Exception as e:
                await message.answer(f"خطا در ارسال پیام: {e}")
            return
        if action == "quota_get_user":
            if message.text and message.text.isdigit():
                target_uid = int(message.text)
                s["admin"]["target_uid"] = target_uid
                s["admin"]["action"] = "quota_get_value"
                await message.answer(f"سهمیه جدید برای کاربر {target_uid} را وارد کنید (مثال: 10):")
            else:
                await message.answer("آیدی عددی نامعتبر است. لطفا دوباره تلاش کنید.")
            return
        if action == "quota_get_value":
            target_uid = s["admin"].get("target_uid")
            s["admin"]["action"] = None
            if message.text and message.text.isdigit():
                new_quota = int(message.text)
                if target_uid in USERS:
                    USERS[target_uid]["daily_limit"] = new_quota
                    await message.answer(f"سهمیه کاربر {target_uid} به {new_quota} تغییر یافت.")
                else:
                    await message.answer("کاربر مورد نظر در سیستم یافت نشد.")
            else:
                await message.answer("مقدار سهمیه نامعتبر است. لطفا یک عدد وارد کنید.")
            return
    if s.get("await_feedback") and message.text:
        s["await_feedback"] = False
        await message.answer("ممنون از بازخوردت", reply_markup=back_to_menu_kb(is_admin))
        return
    pack_wizard = s.get("pack_wizard", {})
    if pack_wizard.get("step") == "awaiting_name" and message.text:
        global BOT_USERNAME
        if not BOT_USERNAME:
            bot_info = await message.bot.get_me()
            BOT_USERNAME = bot_info.username
        pack_name = message.text.strip()
        pack_name_lower = pack_name.lower()
        if any(word in pack_name_lower for word in FORBIDDEN_WORDS):
            await message.answer("نام پک انتخاب شده نامناسب است. لطفاً از کلمات مناسب و بدون کاراکترهای خاص استفاده کنید.", reply_markup=back_to_menu_kb(is_admin))
            return
        if not is_valid_pack_name(pack_name):
            await message.answer(
                "نام پک نامعتبر است. لطفا طبق قوانین یک نام جدید انتخاب کنید:\n\n"
                "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
                "• باید با حرف شروع شود\n"
                "• نباید با زیرخط تمام شود\n"
                "• نباید دو زیرخط پشت سر هم داشته باشد\n"
                "• حداکثر ۵۰ کاراکتر",
                reply_markup=back_to_menu_kb(is_admin)
            )
            return
        short_name = f"{pack_name}_by_{BOT_USERNAME}"
        mode = pack_wizard.get("mode")
        if len(short_name) > 64:
            await message.answer(
                f"نام پک خیلی طولانی است. با اضافه شدن '_by_{BOT_USERNAME}' به {len(short_name)} کاراکتر می‌رسد.\n"
                "لطفا یک نام کوتاه‌تر انتخاب کنید.",
                reply_markup=back_to_menu_kb(is_admin)
            )
            return
        try:
            pack_exists = await check_pack_exists(message.bot, short_name)
            if pack_exists:
                s["current_pack_short_name"] = short_name
                s["current_pack_title"] = pack_name
                s["pack_wizard"] = {}
                add_user_pack(uid, pack_name, short_name)
                await message.answer(f"استیکرها به پک موجود «{pack_name}» اضافه خواهند شد.")
            else:
                dummy_img = render_image("First", "center", "center", "Default", "#FFFFFF", "medium", as_webp=True)
                sticker_to_add = InputSticker(
                    sticker=BufferedInputFile(dummy_img, filename="sticker.webp"),
                    emoji_list=["🎉"]
                )
                try:
                    await message.bot.create_new_sticker_set(
                        user_id=uid, name=short_name, title=pack_name,
                        stickers=[sticker_to_add], sticker_type='regular', sticker_format='static'
                    )
                except pydantic_core.ValidationError as e:
                    if "result.is_animated" in str(e) and "result.is_video" in str(e):
                        print(f"Ignoring known aiogram validation error for pack {short_name}")
                    else:
                        raise e
                s["current_pack_short_name"] = short_name
                s["current_pack_title"] = pack_name
                s["pack_wizard"] = {}
                add_user_pack(uid, pack_name, short_name)
                pack_link = f"https://t.me/addstickers/{short_name}"
                await message.answer(f"پک استیکر «{pack_name}» با موفقیت ساخته شد!\n\n{pack_link}\n\nحالا استیکر بعدی خود را بسازید.")
            if mode == "simple":
                s["mode"] = "simple"
                s["simple"] = {"text": None, "bg_mode": "transparent", "bg_photo_bytes": None}
                await message.answer("متن استیکر ساده رو بفرست:", reply_markup=back_to_menu_kb(is_admin))
            elif mode == "ai":
                s["mode"] = "ai"
                s["ai"] = {
                    "text": None, "v_pos": "center", "h_pos": "center", "font": "Default",
                    "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None
                }
                await message.answer("نوع استیکر پیشرفته را انتخاب کنید:", reply_markup=ai_type_kb())
        except TelegramBadRequest as e:
            await message.answer(f"خطا در ساخت پک: {e.message}", reply_markup=back_to_menu_kb(is_admin))
        except Exception as e:
            traceback.print_exc()
            await message.answer(f"خطای غیرمنتظره‌ای رخ داد: {str(e)}", reply_markup=back_to_menu_kb(is_admin))
        return
    if s["mode"] == "simple":
        s["simple"]["text"] = message.text
        img = render_image(
            text=message.text, v_pos="center", h_pos="center", font_key="Default",
            color_hex="#FFFFFF", size_key="medium", bg_mode=s["simple"].get("bg_mode", "transparent"),
            bg_photo=s["simple"].get("bg_photo_bytes"), as_webp=False
        )
        file_obj = BufferedInputFile(img, filename="preview.png")
        await message.answer_photo(
            file_obj, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple")
        )
        return
    if s["mode"] == "ai":
        if s["ai"].get("awaiting_bg_photo") and message.photo:
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            s["ai"]["bg_photo_bytes"] = downloaded_file
            s["ai"]["awaiting_bg_photo"] = False
            await message.answer("عکس به عنوان پس‌زمینه تنظیم شد. حالا موقعیت متن را انتخاب کنید:", reply_markup=ai_vpos_kb())
            return
        if s["ai"].get("sticker_type") == "image":
            s["ai"]["text"] = message.text
            await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
            return
        if s["ai"].get("sticker_type") == "video" and message.video:
            await message.answer("در حال پردازش ویدیو...")
            video = message.video
            file_info = await bot.get_file(video.file_id)
            downloaded_file = await bot.download_file(file_info.file_path)
            webm_bytes = await process_video_to_webm(downloaded_file)
            if webm_bytes:
                s["last_video_sticker"] = webm_bytes
                await message.answer_sticker(BufferedInputFile(webm_bytes, filename="sticker.webm"))
                await message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
            else:
                await message.answer("پردازش ویدیو با خطا مواجه شد. لطفا دوباره تلاش کنید.")
            return
