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

def available_font_options() -> List[Tuple[str, str]]:
    keys = list(_LOCAL_FONTS.keys())
    return [(k, k) for k in keys[:8]] if keys else [("Default", "Default")]

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

def is_persian(text):
    if not text:
        return False
    persian_pattern = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
    return bool(persian_pattern.search(text))

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

# ============ کیبوردها ============
def main_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر ساده", callback_data="menu:simple")
    kb.button(text="استیکر هوش مصنوعی", callback_data="menu:ai")
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

def add_to_pack_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="افزودن به پک جدید", callback_data="pack:start_creation")
    kb.button(text="نه، لازم نیست", callback_data="pack:skip")
    kb.adjust(2)
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
async def on_start(message: Message):
    reset_mode(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "سلام! خوش آمدید\n"
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
        "راهنما\n\n"
        "• استیکر ساده: متن بدون تنظیمات پیشرفته\n"
        "• استیکر هوش مصنوعی: تنظیمات پیشرفته\n"
        "• سهمیه امروز: محدودیت استفاده\n"
        "• پشتیبانی: ارتباط با پشتیبانی"
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

@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery):
    s = sess(cb.from_user.id)
    s["mode"] = "simple"
    s["simple"] = {"text": None, "bg_mode": "transparent", "bg_photo_bytes": None}
    await cb.message.answer(
        "متن استیکر ساده رو بفرست:",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data.startswith("simple:bg:"))
async def on_simple_bg(cb: CallbackQuery):
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
                text=s["text"],
                v_pos="center", h_pos="center",
                font_key="Default",
                color_hex="#FFFFFF",
                size_key="medium",
                bg_mode=mode,
                bg_photo=s.get("bg_photo_bytes"),
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
        v_pos="center", h_pos="center",
        font_key="Default",
        color_hex="#FFFFFF",
        size_key="medium",
        bg_mode=s.get("bg_mode") or "transparent",
        bg_photo=s.get("bg_photo_bytes"),
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

@router.callback_query(F.data == "menu:ai")
async def on_ai(cb: CallbackQuery):
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)

    if left <= 0 and not is_admin:
        await cb.message.answer(
            "سهمیه امروز تمام شد!",
            reply_markup=back_to_menu_kb(is_admin)
        )
        await cb.answer()
        return

    s = sess(cb.from_user.id)
    s["mode"] = "ai"
    s["ai"] = {
        "text": None, "v_pos": "center", "h_pos": "center", "font": "Default",
        "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None
    }

    await cb.message.answer(
        "نوع استیکر هوش مصنوعی را انتخاب کنید:",
        reply_markup=ai_type_kb()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("ai:type:"))
async def on_ai_type(cb: CallbackQuery):
    sticker_type = cb.data.split(":")[-1]
    s = sess(cb.from_user.id)
    s["ai"]["sticker_type"] = sticker_type

    if sticker_type == "image":
        await cb.message.answer("منبع استیکر تصویری را انتخاب کنید:", reply_markup=ai_image_source_kb())
    elif sticker_type == "video":
        if not is_ffmpeg_installed():
            await cb.message.answer(
                "قابلیت ویدیو فعال نیست.",
                reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
            )
        else:
            await cb.message.answer("یک فایل ویدیو ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "ai:source:text")
async def on_ai_source_text(cb: CallbackQuery):
    await cb.message.answer("متن استیکر را بفرست:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "ai:source:photo")
async def on_ai_source_photo(cb: CallbackQuery):
    sess(cb.from_user.id)["ai"]["awaiting_bg_photo"] = True
    await cb.message.answer("عکس را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("ai:vpos:"))
async def on_ai_vpos(cb: CallbackQuery):
    v_pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["v_pos"] = v_pos
    await cb.message.answer("موقعیت افقی متن:", reply_markup=ai_hpos_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ai:hpos:"))
async def on_ai_hpos(cb: CallbackQuery):
    h_pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["h_pos"] = h_pos

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

    ai_data = sess(cb.from_user.id)["ai"]
    img = render_image(
        text=ai_data.get("text") or "متن ساده",
        v_pos=ai_data["v_pos"],
        h_pos=ai_data["h_pos"],
        font_key="Default",
        color_hex=ai_data["color"],
        size_key=size,
        bg_mode="transparent",
        bg_photo=ai_data.get("bg_photo_bytes"),
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
        v_pos=ai_data["v_pos"],
        h_pos=ai_data["h_pos"],
        font_key="Default",
        color_hex=ai_data["color"],
        size_key=ai_data["size"],
        bg_mode="transparent",
        bg_photo=ai_data.get("bg_photo_bytes"),
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
    await cb.message.answer(
        "موقعیت عمودی متن:",
        reply_markup=ai_vpos_kb()
    )
    await cb.answer()

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
    await cb.message.answer("چه چیزی رو دوست نداشتی؟")
    await cb.answer()

@router.callback_query(F.data == "pack:skip")
async def on_pack_skip(cb: CallbackQuery):
    await cb.message.answer(
        "باشه، اضافه نکردم.",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "pack:start_creation")
async def on_pack_start_creation(cb: CallbackQuery):
    s = sess(cb.from_user.id)
    s["pack_wizard"] = {"step": "awaiting_name"}
    rules_text = (
        "برای ایجاد پک جدید، یک نام انگلیسی ارسال کنید.\n\n"
        "• فقط حروف انگلیسی، عدد و زیرخط\n"
        "• حداکثر ۳۲ کاراکتر"
    )
    await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

async def _handle_pack_creation(user_id: int, pack_title: str, bot: Bot, message_to_reply: Message):
    s = sess(user_id)
    sticker_bytes = s.get("last_sticker")

    if not sticker_bytes:
        await message_to_reply.answer("استیکری برای افزودن وجود ندارد.")
        s["pack_wizard"] = {}
        return

    base_short_name = re.sub(r'\W+', '_', pack_title, flags=re.UNICODE).lower()
    short_name = f"{base_short_name}_by_{user_id}_bot"

    try:
        sticker_to_add = InputSticker(
            sticker=BufferedInputFile(sticker_bytes, filename="sticker.webp"),
            emoji="😀"
        )

        await bot.create_new_sticker_set(
            user_id=user_id,
            name=short_name,
            title=pack_title,
            stickers=[sticker_to_add],
            sticker_type='regular',
            sticker_format='static'
        )

        pack_link = f"https://t.me/addstickers/{short_name}"
        await bot.send_message(
            chat_id=user_id,
            text=f"پک استیکر «{pack_title}» با موفقیت ساخته شد!\n{pack_link}"
        )

        s["pack_wizard"] = {}

    except TelegramBadRequest as e:
        await message_to_reply.answer(f"خطا در ساخت پک: {e.message}")
        s["pack_wizard"] = {}
    except Exception as e:
        await message_to_reply.answer(f"خطای غیرمنتظره: {e}")
        s["pack_wizard"] = {}

@router.message()
async def on_message(message: Message):
    uid = message.from_user.id
    s = sess(uid)

    if s.get("await_feedback") and message.text:
        s["await_feedback"] = False
        await message.answer(
            "ممنون از بازخوردت",
            reply_markup=back_to_menu_kb(uid == ADMIN_ID)
        )
        return

    pack_wizard = s.get("pack_wizard", {})
    if pack_wizard.get("step") == "awaiting_name" and message.text:
        pack_name = message.text.strip()
        s["pack_wizard"]["name"] = pack_name
        await _handle_pack_creation(uid, pack_name, message.bot, message)
        return

    if message.photo:
        if s.get("mode") == "simple" and s["simple"].get("awaiting_bg_photo"):
            file = await message.bot.download(message.photo[-1].file_id)
            s["simple"]["bg_photo_bytes"] = file.read()
            s["simple"]["awaiting_bg_photo"] = False
            if s["simple"].get("text"):
                img = render_image(
                    text=s["simple"]["text"],
                    v_pos="center",
                    h_pos="center",
                    font_key="Default",
                    color_hex="#FFFFFF",
                    size_key="medium",
                    bg_photo=s["simple"]["bg_photo_bytes"],
                    as_webp=False
                )
                await message.answer_photo(BufferedInputFile(img, "preview.png"), caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
            else:
                await message.answer("عکس دریافت شد. حالا متن را بفرستید:")
        elif s.get("mode") == "ai" and s["ai"].get("awaiting_bg_photo"):
            file = await message.bot.download(message.photo[-1].file_id)
            s["ai"]["bg_photo_bytes"] = file.read()
            s["ai"]["awaiting_bg_photo"] = False
            await message.answer("عکس دریافت شد. حالا متن را بفرستید:")
        return

    if message.video and s.get("mode") == "ai" and s["ai"].get("sticker_type") == "video":
        await message.answer("در حال پردازش ویدیو...")
        file = await message.bot.download(message.video.file_id)
        webm_bytes = await process_video_to_webm(file.read())

        if webm_bytes:
            sess(uid)["last_sticker"] = webm_bytes
            await message.answer_sticker(BufferedInputFile(webm_bytes, "sticker.webm"))
            await message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
        else:
            await message.answer("پردازش ویدیو با خطا مواجه شد.", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
        return

    mode = s.get("mode", "menu")

    if mode == "simple":
        if message.text:
            s["simple"]["text"] = message.text.strip()
            await message.answer("پس‌زمینه رو انتخاب کن:", reply_markup=simple_bg_kb())
    elif mode == "ai":
        if message.text and s["ai"].get("sticker_type") == "image":
            u = user(uid)
            is_admin = (uid == ADMIN_ID)
            left = _quota_left(u, is_admin)
            if left <= 0 and not is_admin:
                await message.answer("سهمیه تمام شد!", reply_markup=back_to_menu_kb(is_admin))
                return
            s["ai"]["text"] = message.text.strip()
            await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
    else:
        is_admin = (uid == ADMIN_ID)
        await message.answer("از منوی زیر انتخاب کن:", reply_markup=main_menu_kb(is_admin))

# You need to add the main execution block to run the bot
async def main():
    dp = Dispatcher()
    dp.include_router(router)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
