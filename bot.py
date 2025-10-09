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
BOT_TOKEN = os.getenv("BOT_TOKEN", "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در محیط تنظیم کنید.")

CHANNEL_USERNAME = "@redoxbot_sticker"  # عضویت اجباری
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919

MAINTENANCE = False  # حالت نگهداری بخش AI
DAILY_LIMIT = 5      # سهمیه روزانه AI (ادمین نامحدود)
BOT_USERNAME = ""    # بعداً در main پر می‌شود

# ============ حافظه ساده (in-memory) ============
USERS: Dict[int, Dict[str, Any]] = {}     # {user_id: {ai_used:int, vote:str|None, day_start:int, pack:{title,name,created:bool}}}
SESSIONS: Dict[int, Dict[str, Any]] = {}  # {user_id: {"mode":..., "ai":{}, "simple":{}, "pack_wizard":{}, "await_feedback":bool, "last_sticker":bytes, "last_video_sticker":bytes}}
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
        SESSIONS[uid] = {"mode": "menu", "ai": {}, "simple": {}, "pack_wizard": {}, "await_feedback": False, "last_sticker": None, "last_video_sticker": None}
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

def infer_from_text(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    t = (text or "").strip()
    for k, v in POS_WORDS.items():
        if k in t:
            out["position"] = v
            break
    for k, v in SIZE_WORDS.items():
        if k in t:
            out["size"] = v
            break
    for name, hx in NAME_TO_HEX.items():
        if name in t:
            out["color"] = hx
            break
    m = re.search(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", t)
    if m:
        out["color"] = "#" + m.group(1)
    return out

# ============ فونت‌های محلی ============
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
LOCAL_FONT_FILES = {
    "Vazirmatn": ["Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf"],
    "NotoNaskh": ["NotoNaskhArabic-Regular.ttf", "NotoNaskhArabic-Medium.ttf"],
    "Sahel": ["Sahel.ttf", "Sahel-Bold.ttf"],
    "IRANSans": ["IRANSans.ttf", "IRANSansX-Regular.ttf"],
    "Default": ["NotoNaskhArabic-Regular.ttf", "Vazirmatn-Regular.ttf", "Sahel.ttf"],
}

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

def resolve_font_path(font_key: Optional[str]) -> str:
    if font_key and font_key in _LOCAL_FONTS:
        return _LOCAL_FONTS[font_key]
    return next(iter(_LOCAL_FONTS.values()), "")

# ============ رندر تصویر/استیکر ============
CANVAS = (512, 512)

def _prepare_text(text: str) -> str:
    if not text:
        return ""
    
    # استفاده از arabic_reshaper برای اتصال حروف فارسی
    reshaped_text = arabic_reshaper.reshape(text.strip())
    
    # استفاده از bidi برای ترتیب صحیح راست به چپ
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

def wrap_text_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
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
    size = base
    while size > 12:  # کاهش حداقل سایز برای اطمینان از جا شدن متن
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        lines = wrap_text_to_width(draw, text, font, max_w)
        bbox = draw.multiline_textbbox((0, 0), "\n".join(lines), font=font, spacing=4, align="center", stroke_width=2)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h:
            return size
        size -= 1  # کاهش تدریجی‌تر سایز
    return max(size, 12)

def _make_default_bg(size=(512, 512)) -> Image.Image:
    tpl_dir = os.path.join(os.path.dirname(__file__), "templates")
    candidates = ["gradient.png", "gradient.webp", "default.png", "default.webp"]
    for name in candidates:
        p = os.path.join(tpl_dir, name)
        if os.path.isfile(p):
            try:
                img = Image.open(p).convert("RGBA")
                if img.size != size:
                    img = img.resize(size, Image.LANCZOS)
                return img
            except Exception:
                pass
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

def _compose_bg_photo(photo_bytes: bytes, size=(512, 512)) -> Image.Image:
    base = Image.open(BytesIO(photo_bytes)).convert("RGBA")
    bw, bh = base.size
    scale = max(size[0] / bw, size[1] / bh)
    nw, nh = int(bw * scale), int(bh * scale)
    base = base.resize((nw, nh), Image.LANCZOS)
    x = (nw - size[0]) // 2
    y = (nh - size[1]) // 2
    base = base.crop((x, y, x + size[0], y + size[1]))
    return base

def render_image(text: str, position: str, font_key: str, color_hex: str, size_key: str, bg_mode: str = "transparent", bg_photo: Optional[bytes] = None, as_webp: bool = False) -> bytes:
    W, H = CANVAS
    if bg_mode == "default":
        img = _make_default_bg((W, H))
    elif bg_mode == "photo" and bg_photo:
        img = _compose_bg_photo(bg_photo, (W, H))
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = _parse_hex(color_hex)
    padding = 28
    box_w, box_h = W - 2 * padding, H - 2 * padding

    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)

    font_path = resolve_font_path(font_key)
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
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6, align="center", stroke_width=2)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    if position == "top":
        y = padding + th / 2
    elif position == "bottom":
        y = H - padding - th / 2
    else:
        y = H / 2

    draw.multiline_text(
        (W / 2, y),
        wrapped,
        font=font,
        fill=color,
        anchor="mm",
        align="center",
        spacing=6,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 220)
    )

    buf = BytesIO()
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

# ============ پردازش ویدیو ============
def _check_ffmpeg() -> bool:
    """بررسی وجود ffmpeg در سیستم"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def process_video_to_webm(video_bytes: bytes, max_duration: int = 10) -> bytes:
    """تبدیل ویدیو به فرمت WebM برای استیکر ویدیویی تلگرام"""
    if not _check_ffmpeg():
        raise Exception("FFmpeg نصب نیست. لطفاً FFmpeg را نصب کنید:\n- Windows: https://ffmpeg.org/download.html\n- Ubuntu: sudo apt install ffmpeg\n- CentOS: sudo yum install ffmpeg")
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as input_file:
        input_file.write(video_bytes)
        input_path = input_file.name
    
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as output_file:
        output_path = output_file.name
    
    try:
        # تنظیمات خاص برای استیکر ویدیویی تلگرام
        cmd = [
            'ffmpeg', '-i', input_path,
            '-t', str(max_duration),
            '-vf', 'scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2',
            '-c:v', 'libvpx-vp9',
            '-crf', '30',
            '-b:v', '400k',
            '-maxrate', '400k',
            '-bufsize', '800k',
            '-an',  # حذف صدا برای استیکر
            '-f', 'webm',
            '-deadline', 'good',
            '-cpu-used', '0',
            '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            with open(output_path, 'rb') as f:
                webm_data = f.read()
            return webm_data
        else:
            raise Exception(f"خطا در تبدیل ویدیو: {result.stderr}")
    
    finally:
        # پاک کردن فایل‌های موقت
        try:
            os.unlink(input_path)
            os.unlink(output_path)
        except:
            pass
    
    raise Exception("تبدیل ویدیو ناموفق بود")

def add_text_to_video(video_bytes: bytes, text: str, position: str, font_key: str, color_hex: str, size_key: str) -> bytes:
    """اضافه کردن متن به ویدیو با پشتیبانی کامل از فونت فارسی"""
    if not _check_ffmpeg():
        raise Exception("FFmpeg نصب نیست. لطفاً FFmpeg را نصب کنید:\n- Windows: https://ffmpeg.org/download.html\n- Ubuntu: sudo apt install ffmpeg\n- CentOS: sudo yum install ffmpeg")
    
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as input_file:
        input_file.write(video_bytes)
        input_path = input_file.name
    
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as output_file:
        output_path = output_file.name
    
    # ایجاد فایل فونت موقت برای فارسی
    font_path = resolve_font_path(font_key)
    if not font_path or not os.path.exists(font_path):
        # استفاده از فونت پیش‌فرض سیستم
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    try:
        # تنظیم موقعیت متن
        if position == "top":
            y_pos = "80"
        elif position == "bottom":
            y_pos = "h-80"
        else:  # center
            y_pos = "(h-text_h)/2"
        
        # تنظیم اندازه فونت
        size_map = {"small": 36, "medium": 52, "large": 68}
        font_size = size_map.get(size_key, 52)
        
        # آماده‌سازی متن فارسی
        prepared_text = _prepare_text(text)
        
        # استفاده از ffmpeg برای اضافه کردن متن با فونت فارسی
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', f"drawtext=text='{prepared_text}':fontfile='{font_path}':fontsize={font_size}:fontcolor=white:x=(w-text_w)/2:y={y_pos}:box=1:boxcolor=black@0.7:boxborderw=10",
            '-c:v', 'libvpx-vp9',
            '-crf', '30',
            '-b:v', '400k',
            '-maxrate', '400k',
            '-bufsize', '800k',
            '-an',  # حذف صدا
            '-f', 'webm',
            '-deadline', 'good',
            '-cpu-used', '0',
            '-y', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            with open(output_path, 'rb') as f:
                output_data = f.read()
            return output_data
        else:
            raise Exception(f"خطا در اضافه کردن متن: {result.stderr}")
    
    finally:
        try:
            os.unlink(input_path)
            os.unlink(output_path)
        except:
            pass
    
    raise Exception("اضافه کردن متن به ویدیو ناموفق بود")

# ============ ابزار پک ============
def _normalize_shortname(base: str) -> str:
    # فقط حروف/عدد/زیرخط، کوچک‌سازی
    base = re.sub(r"[^a-zA-Z0-9_]", "", base or "").lower()
    base = base[:32] if len(base) > 32 else base
    if not base:
        base = "pack"
    # پایان لازم: _by_<botusername>
    suffix = f"_by_{BOT_USERNAME}".lower()
    if not base.endswith(suffix):
        base = f"{base}{suffix}"
    return base

async def _ensure_pack_created(bot: Bot, uid: int, webp_bytes: bytes) -> Tuple[bool, str]:
    # True اگر ساخته شد یا وجود داشت
    u = user(uid)
    pack = u.get("pack")
    if not pack or not pack.get("name") or not pack.get("title"):
        return (False, "اطلاعات پک کامل نیست.")
    name = _normalize_shortname(pack["name"])
    title = pack["title"]
    if pack.get("created"):
        return (True, name)
    try:
        input_sticker = InputSticker(
            sticker=BufferedInputFile(webp_bytes, filename="sticker.webp"),
            emoji_list=["🙂"]
        )
        await bot.create_new_sticker_set(
            user_id=uid,
            name=name,
            title=title,
            stickers=[input_sticker],
            sticker_format="static"
        )
        u["pack"]["created"] = True
        return (True, name)
    except Exception as e:
        # اگر قبلاً وجود داشته، created را True کن تا add کار کند
        if "STICKERSET_INVALID" in str(e) or "stickerset_invalid" in str(e):
            u["pack"]["created"] = True
            return (True, name)
        return (False, f"ساخت پک نشد: {e}")

async def _add_to_pack(bot: Bot, uid: int, webp_bytes: bytes) -> str:
    ok, res = await _ensure_pack_created(bot, uid, webp_bytes)
    if not ok:
        return res
    name = res
    # اگر پک تازه ساخته شد، همین استیکر داخلش هست؛ برای دفعات بعدی اضافه می‌کنیم
    u = user(uid)
    if u["pack"].get("just_created_once"):
        # جلوگیری از افزودن دوباره همان استیکر اول
        u["pack"]["just_created_once"] = False
        return f"پک شما آماده است: https://t.me/addstickers/{name}"
    try:
        input_sticker = InputSticker(
            sticker=BufferedInputFile(webp_bytes, filename="sticker.webp"),
            emoji_list=["🙂"]
        )
        await bot.add_sticker_to_set(
            user_id=uid,
            name=name,
            sticker=input_sticker
        )
        return f"به پک اضافه شد ✅\nلینک پک: https://t.me/addstickers/{name}"
    except Exception as e:
        return f"افزودن به پک نشد: {e}"

async def _add_video_to_pack(bot: Bot, uid: int, webm_bytes: bytes) -> str:
    """افزودن استیکر ویدیویی به پک"""
    u = user(uid)
    pack = u.get("pack")
    if not pack or not pack.get("name") or not pack.get("title"):
        return "اطلاعات پک کامل نیست."
    
    name = _normalize_shortname(pack["name"])
    title = pack["title"]
    
    # برای استیکر ویدیویی، پک جدید ایجاد کن
    try:
        input_sticker = InputSticker(
            sticker=BufferedInputFile(webm_bytes, filename="video_sticker.webm"),
            emoji_list=["🎬"],
            format="video"
        )
        
        if not pack.get("created"):
            # ایجاد پک جدید با استیکر ویدیویی
            await bot.create_new_sticker_set(
                user_id=uid,
                name=name,
                title=title,
                stickers=[input_sticker],
                sticker_format="video"
            )
            u["pack"]["created"] = True
            return f"پک استیکر ویدیویی ایجاد شد ✅\nلینک پک: https://t.me/addstickers/{name}"
        else:
            # اضافه کردن به پک موجود
            await bot.add_sticker_to_set(
                user_id=uid,
                name=name,
                sticker=input_sticker
            )
            return f"استیکر ویدیویی به پک اضافه شد ✅\nلینک پک: https://t.me/addstickers/{name}"
    except Exception as e:
        return f"افزودن استیکر ویدیویی به پک نشد: {e}"

# ============ کیبوردها ============
def main_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر ساده 🪄", callback_data="menu:simple")
    kb.button(text="استیکر هوش مصنوعی 🤖", callback_data="menu:ai")
    kb.button(text="سهمیه امروز ⏳", callback_data="menu:quota")
    kb.button(text="راهنما ℹ️", callback_data="menu:help")
    kb.button(text="اشتراک / نظرسنجی 📊", callback_data="menu:sub")
    kb.button(text="پشتیبانی 🛟", callback_data="menu:support")
    if is_admin:
        kb.button(text="پنل ادمین 🛠", callback_data="menu:admin")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

def join_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="عضویت در کانال 🔗", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
    kb.button(text="عضو شدم ✅", callback_data="check_sub")
    kb.adjust(1, 1)
    return kb.as_markup()

def back_to_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="بازگشت به منو ⬅️", callback_data="menu:home")
    if is_admin:
        kb.button(text="پنل ادمین 🛠", callback_data="menu:admin")
    kb.adjust(1, 1)
    return kb.as_markup()

def yes_no_kb(yes_cb: str, no_cb: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="بله ✅", callback_data=yes_cb)
    kb.button(text="خیر ❌", callback_data=no_cb)
    kb.adjust(2)
    return kb.as_markup()

def simple_bg_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="شفاف ♻️", callback_data="simple:bg:transparent")
    kb.button(text="پیش‌فرض 🎨", callback_data="simple:bg:default")
    kb.button(text="ارسال عکس 🖼", callback_data="simple:bg:want_photo")
    kb.adjust(3)
    return kb.as_markup()

def after_preview_kb(prefix: str):
    # prefix: simple یا ai
    kb = InlineKeyboardBuilder()
    kb.button(text="تایید ✅", callback_data=f"{prefix}:confirm")
    kb.button(text="ویرایش ✏️", callback_data=f"{prefix}:edit")
    kb.button(text="بازگشت ⬅️", callback_data="menu:home")
    kb.adjust(2, 1)
    return kb.as_markup()

def rate_kb():
    return yes_no_kb("rate:yes", "rate:no")

def add_to_pack_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="افزودن به پک 📦", callback_data="pack:add")
    kb.button(text="نه، لازم نیست", callback_data="pack:skip")
    kb.adjust(2)
    return kb.as_markup()

# ============ عضویت اجباری ============
async def is_member(bot: Bot, uid: int) -> bool:
    try:
        cm = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=uid)
        return cm.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
    except TelegramBadRequest:
        return True
    except Exception:
        return False

async def ensure_membership(message_or_cb) -> bool:
    uid = message_or_cb.from_user.id
    bot = message_or_cb.bot
    ok = await is_member(bot, uid)
    if not ok:
        text = f"برای استفاده، ابتدا در کانال {CHANNEL_USERNAME} عضو شوید سپس دکمه «عضو شدم ✅» را بزنید."
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, reply_markup=join_kb())
        else:
            await message_or_cb.message.answer(text, reply_markup=join_kb())
            await message_or_cb.answer()
        return False
    return True

# ============ ویزارد ساخت پک ============
async def need_pack_setup(uid: int) -> bool:
    u = user(uid)
    return not u.get("pack") or not u["pack"].get("title") or not u["pack"].get("name")

async def start_pack_wizard(message_or_cb, uid: int):
    s = sess(uid)
    s["mode"] = "pack_wizard"
    s["pack_wizard"] = {"stage": "ask_name"}
    await (message_or_cb.message if isinstance(message_or_cb, CallbackQuery) else message_or_cb).answer(
        "نام پک را بنویس (مثال: my_stickers):\n"
        "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
        "• باید با حرف شروع شود\n"
        "• حداکثر ۳۲ کاراکتر"
    )

# ============ ربات و روتر ============
router = Router()

@router.message(CommandStart())
async def on_start(message: Message):
    reset_mode(message.from_user.id)
    if not await ensure_membership(message):
        return
    await message.answer("سلام! خوش اومدی ✨\nیکی از گزینه‌های زیر رو انتخاب کن:", reply_markup=main_menu_kb(is_admin=(message.from_user.id == ADMIN_ID)))

@router.callback_query(F.data == "check_sub")
async def on_check_sub(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    await cb.message.answer("عالی! حالا از منو یکی را انتخاب کن:", reply_markup=main_menu_kb(is_admin=(cb.from_user.id == ADMIN_ID)))
    await cb.answer("عضویت تایید شد ✅")

# ----- منوها -----
@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    reset_mode(cb.from_user.id)
    await cb.message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin=(cb.from_user.id == ADMIN_ID)))
    await cb.answer()

@router.callback_query(F.data == "menu:support")
async def on_support(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    await cb.message.answer(f"پشتیبانی: {SUPPORT_USERNAME}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer("باز شد")

@router.callback_query(F.data == "menu:help")
async def on_help(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    txt = (
        "راهنما ℹ️\n"
        "• استیکر ساده 🪄: متن بده؛ پس‌زمینه را انتخاب کن (شفاف/پیش‌فرض/عکس)، پیش‌نمایش بگیر و تایید کن. بعد از تایید می‌تونی به پک خودت اضافه کنی.\n"
        "• استیکر هوش مصنوعی 🤖: متن بده؛ موقعیت، فونت، رنگ، اندازه و پس‌زمینه را انتخاب کن؛ پیش‌نمایش و تایید. بعد از تایید می‌تونی به پک اضافه کنی.\n"
        "• سهمیه امروز ⏳: تعداد باقی‌مانده امروز و زمان تمدید سهمیه AI را می‌بینی.\n"
        "• اشتراک / نظرسنجی 📊: رأی بده که اشتراک اضافه شود یا نه.\n"
        "• پشتیبانی 🛟: ارتباط با پشتیبانی.\n"
        "• نکته پک: قبل از ساخت اولین استیکر، عنوان و نام پک را وارد کن. نام باید انگلیسی باشد؛ آخرش خودکار به شکل _by_نام‌بات تنظیم می‌شود."
    )
    await cb.message.answer(txt, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer("نمایش راهنما")

@router.callback_query(F.data == "menu:quota")
async def on_quota(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    eta = _fmt_eta(_seconds_to_reset(u))
    quota_txt = "نامحدود" if is_admin else f"{left} از {DAILY_LIMIT}"
    await cb.message.answer(f"سهمیه امروز: {quota_txt}\nتمدید در: {eta}", reply_markup=back_to_menu_kb(is_admin))
    await cb.answer()

@router.callback_query(F.data == "menu:sub")
async def on_sub(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    u = user(cb.from_user.id)
    yes = sum(1 for v in USERS.values() if v.get("vote") == "yes")
    no = sum(1 for v in USERS.values() if v.get("vote") == "no")
    kb = InlineKeyboardBuilder()
    kb.button(text="بله ✅", callback_data="vote:yes")
    kb.button(text="خیر ❌", callback_data="vote:no")
    kb.button(text="بازگشت ⬅️", callback_data="menu:home")
    kb.adjust(2, 1)
    yours = "بله" if u.get("vote") == "yes" else ("خیر" if u.get("vote") == "no" else "ثبت نشده")
    await cb.message.answer(f"اشتراک بیاریم؟\nرأی شما: {yours}\nآمار فعلی: بله {yes} | خیر {no}", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("vote:")))
async def on_vote(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    choice = cb.data.split(":", 1)[1]
    if choice in ("yes", "no"):
        user(cb.from_user.id)["vote"] = choice
        await cb.answer("رأی ثبت شد ✅")
    else:
        await cb.answer("نامعتبر")
    yes = sum(1 for v in USERS.values() if v.get("vote") == "yes")
    no = sum(1 for v in USERS.values() if v.get("vote") == "no")
    txt = f"اشتراک بیاریم؟\nرأی شما: {'بله' if choice == 'yes' else 'خیر'}\nآمار فعلی: بله {yes} | خیر {no}"
    await cb.message.edit_text(txt, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))

# ----- استیکر ساده -----
@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    if await need_pack_setup(cb.from_user.id):
        return await start_pack_wizard(cb, cb.from_user.id)
    s = sess(cb.from_user.id)
    s["mode"] = "simple"
    s["simple"] = {"state": "ASK_TEXT", "text": None, "bg_mode": None, "bg_photo": None}
    await cb.message.answer("متن استیکر ساده رو بفرست ✍️", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("simple:bg:")))
async def on_simple_bg(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    st = sess(cb.from_user.id)["simple"]
    act = cb.data.split(":")[-1]
    if act == "transparent":
        st["bg_mode"] = "transparent"
    elif act == "default":
        st["bg_mode"] = "default"
    elif act == "want_photo":
        st["state"] = "WAIT_BG_PHOTO"
        await cb.message.answer("عکس پس‌زمینه را ارسال کن 🖼")
        return await cb.answer("منتظر عکس")
    # اگر متن نداریم، برگرد
    if not st.get("text"):
        await cb.answer("اول متن بده", show_alert=True)
        return
    img = render_image(text=st["text"], position="center", font_key="Default", color_hex="#FFFFFF",
                       size_key="medium", bg_mode=st.get("bg_mode") or "transparent", as_webp=False)
    file_obj = BufferedInputFile(img, filename="preview.png")
    await cb.message.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
    await cb.answer("پیش‌نمایش")

@router.callback_query(F.data == "simple:confirm")
async def on_simple_confirm(cb: CallbackQuery):
    st = sess(cb.from_user.id)["simple"]
    webp = render_image(text=st["text"], position="center", font_key="Default", color_hex="#FFFFFF",
                        size_key="medium", bg_mode=st.get("bg_mode") or "transparent", bg_photo=st.get("bg_photo"), as_webp=True)
    sess(cb.from_user.id)["last_sticker"] = webp
    await cb.message.answer_sticker(BufferedInputFile(webp, filename="sticker.webp"))
    await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
    await cb.answer("ارسال شد")

@router.callback_query(F.data == "simple:edit")
async def on_simple_edit(cb: CallbackQuery):
    await cb.message.answer("پس‌زمینه را انتخاب کن:", reply_markup=simple_bg_kb())
    await cb.answer()

# ----- استیکر هوش مصنوعی -----
@router.callback_query(F.data == "menu:ai")
async def on_ai(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    if await need_pack_setup(cb.from_user.id):
        return await start_pack_wizard(cb, cb.from_user.id)
    if MAINTENANCE:
        await cb.message.answer("بخش هوش مصنوعی موقتاً در دست تعمیر است 🛠", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()
        return
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    eta = _fmt_eta(_seconds_to_reset(u))
    if left <= 0 and not is_admin:
        await cb.message.answer(f"سهمیه امروز تمام شد. تمدید در: {eta}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()
        return
    s = sess(cb.from_user.id)
    s["mode"] = "ai"
    s["ai"] = {"text": None, "position": None, "font": "Default", "color": "#FFFFFF", "size": "large", "bg": "transparent", "bg_photo": None, "video_mode": False, "video_data": None}
    
    # اضافه کردن دکمه انتخاب نوع استیکر
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر تصویری 🖼", callback_data="ai:type:image")
    kb.button(text="استیکر ویدیویی 🎬", callback_data="ai:type:video")
    kb.button(text="بازگشت ⬅️", callback_data="menu:home")
    kb.adjust(2, 1)
    
    await cb.message.answer(f"نوع استیکر را انتخاب کن:\n(سهمیه امروز: {'نامحدود' if is_admin else f'{left} از {DAILY_LIMIT}'} | تمدید: {eta})", reply_markup=kb.as_markup())
    await cb.answer()

async def send_ai_preview(message_or_cb, uid: int):
    a = sess(uid)["ai"]
    img = render_image(
        text=a.get("text") or "",
        position=a.get("position") or "center",
        font_key=a.get("font") or "Default",
        color_hex=a.get("color") or "#FFFFFF",
        size_key=a.get("size") or "medium",
        bg_mode=a.get("bg") or "transparent",
        bg_photo=a.get("bg_photo"),
        as_webp=False
    )
    file_obj = BufferedInputFile(img, filename="preview.png")
    if isinstance(message_or_cb, Message):
        await message_or_cb.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("ai"))
    else:
        await message_or_cb.message.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("ai"))

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:")))
async def on_ai_callbacks(cb: CallbackQuery):
    if not await ensure_membership(cb):
        return
    if MAINTENANCE:
        return await cb.answer("در دست تعمیر 🛠", show_alert=True)

    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)

    a = sess(cb.from_user.id)["ai"]
    parts = cb.data.split(":", 2)
    action = parts[1] if len(parts) > 1 else ""
    value = parts[2] if len(parts) > 2 else ""

    if not is_admin and left <= 0 and action not in ("edit", "type"):
        eta = _fmt_eta(_seconds_to_reset(u))
        return await cb.answer(f"سهمیه امروز تمام شد. تمدید: {eta}", show_alert=True)

    if action == "type":
        if value == "image":
            a["video_mode"] = False
            await cb.message.answer(f"متن استیکر تصویری رو بفرست ✍️")
        elif value == "video":
            a["video_mode"] = True
            await cb.message.answer("ویدیو رو ارسال کن (حداکثر ۱۰ ثانیه) 🎬")
        return await cb.answer("انتخاب شد")

    if action == "pos":
        a["position"] = value
        kb = InlineKeyboardBuilder()
        for label, val in available_font_options():
            kb.button(text=label, callback_data=f"ai:font:{val}")
        kb.adjust(3)
        await cb.message.answer("فونت را انتخاب کن:", reply_markup=kb.as_markup())
        return await cb.answer("ثبت شد")

    if action == "font":
        a["font"] = value
        kb = InlineKeyboardBuilder()
        for name, hx in DEFAULT_PALETTE:
            kb.button(text=name, callback_data=f"ai:color:{hx}")
        kb.adjust(3)
        await cb.message.answer("رنگ متن:", reply_markup=kb.as_markup())
        return await cb.answer("ثبت شد")

    if action == "color":
        a["color"] = value
        kb = InlineKeyboardBuilder()
        for label, val in [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]:
            kb.button(text=label, callback_data=f"ai:size:{val}")
        kb.adjust(3)
        await cb.message.answer("اندازه متن:", reply_markup=kb.as_markup())
        return await cb.answer("ثبت شد")

    if action == "size":
        a["size"] = value
        
        # اگر حالت ویدیویی است، مستقیم پیش‌نمایش نشان بده
        if a.get("video_mode"):
            if all(a.get(k) for k in ["text", "position", "font", "color", "size", "video_data"]):
                await cb.message.answer("پیش‌نمایش ویدیو آماده است!", reply_markup=after_preview_kb("ai"))
                return await cb.answer("آماده برای تایید")
            else:
                return await cb.answer("اطلاعات ناقص است", show_alert=True)
        
        # برای حالت تصویری، گزینه‌های پس‌زمینه نشان بده
        kb = InlineKeyboardBuilder()
        kb.button(text="شفاف ♻️", callback_data="ai:bg:transparent")
        kb.button(text="پیش‌فرض 🎨", callback_data="ai:bg:default")
        kb.button(text="ارسال عکس 🖼", callback_data="ai:bg:photo")
        kb.adjust(3)
        await cb.message.answer("پس‌زمینه:", reply_markup=kb.as_markup())
        return await cb.answer("ثبت شد")

    if action == "bg":
        a["bg"] = value
        if value == "photo":
            a["bg_photo"] = None
            await cb.message.answer("عکس پس‌زمینه را ارسال کن 🖼")
            return await cb.answer("منتظر عکس هستم")
        if all(a.get(k) for k in ["text", "position", "font", "color", "size"]):
            await send_ai_preview(cb, cb.from_user.id)
            return await cb.answer("پیش‌نمایش آماده شد")

    if action == "edit":
        for step in ["position", "font", "color", "size", "bg"]:
            if not a.get(step) or (step == "bg" and a["bg"] == "photo" and not a.get("bg_photo")):
                if step == "position":
                    kb = InlineKeyboardBuilder()
                    for label, val in [("بالا ⬆️", "top"), ("وسط ⚪️", "center"), ("پایین ⬇️", "bottom")]:
                        kb.button(text=label, callback_data=f"ai:pos:{val}")
                    kb.adjust(3)
                    await cb.message.answer("متن کجا قرار بگیرد؟", reply_markup=kb.as_markup())
                elif step == "font":
                    kb = InlineKeyboardBuilder()
                    for label, val in available_font_options():
                        kb.button(text=label, callback_data=f"ai:font:{val}")
                    kb.adjust(3)
                    await cb.message.answer("فونت:", reply_markup=kb.as_markup())
                elif step == "color":
                    kb = InlineKeyboardBuilder()
                    for name, hx in DEFAULT_PALETTE:
                        kb.button(text=name, callback_data=f"ai:color:{hx}")
                    kb.adjust(3)
                    await cb.message.answer("رنگ:", reply_markup=kb.as_markup())
                elif step == "size":
                    kb = InlineKeyboardBuilder()
                    for label, val in [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]:
                        kb.button(text=label, callback_data=f"ai:size:{val}")
                    kb.adjust(3)
                    await cb.message.answer("اندازه:", reply_markup=kb.as_markup())
                elif step == "bg":
                    kb = InlineKeyboardBuilder()
                    kb.button(text="شفاف ♻️", callback_data="ai:bg:transparent")
                    kb.button(text="پیش‌فرض 🎨", callback_data="ai:bg:default")
                    kb.button(text="ارسال عکس 🖼", callback_data="ai:bg:photo")
                    kb.adjust(3)
                    await cb.message.answer("پس‌زمینه:", reply_markup=kb.as_markup())
                return await cb.answer()
        await cb.answer()

    if action == "confirm":
        left = _quota_left(u, is_admin)
        if left <= 0 and not is_admin:
            eta = _fmt_eta(_seconds_to_reset(u))
            return await cb.answer(f"سهمیه امروز تمام شد. تمدید: {eta}", show_alert=True)
        
        if a.get("video_mode"):
            # پردازش استیکر ویدیویی
            if not a.get("video_data"):
                return await cb.answer("ویدیو ارسال نشده", show_alert=True)
            
            try:
                # اضافه کردن متن به ویدیو
                video_with_text = add_text_to_video(
                    a["video_data"],
                    a.get("text") or "",
                    a.get("position") or "center",
                    a.get("font") or "Default",
                    a.get("color") or "#FFFFFF",
                    a.get("size") or "medium"
                )
                sess(cb.from_user.id)["last_video_sticker"] = video_with_text
                
                # ارسال به عنوان استیکر ویدیویی
                await cb.message.answer_sticker(BufferedInputFile(video_with_text, filename="sticker.webm"))
            except Exception as e:
                return await cb.answer(f"خطا در پردازش ویدیو: {str(e)}", show_alert=True)
        else:
            # پردازش استیکر تصویری
            img = render_image(
                text=a.get("text") or "",
                position=a.get("position") or "center",
                font_key=a.get("font") or "Default",
                color_hex=a.get("color") or "#FFFFFF",
                size_key=a.get("size") or "medium",
                bg_mode=a.get("bg") or "transparent",
                bg_photo=a.get("bg_photo"),
                as_webp=True
            )
            sess(cb.from_user.id)["last_sticker"] = img
            await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
        
        if not is_admin:
            u["ai_used"] = int(u.get("ai_used", 0)) + 1
        await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
        return await cb.answer("ارسال شد")

# ============ مدیریت پیام‌ها ============
@router.message()
async def on_message(message: Message):
    uid = message.from_user.id
    if not await ensure_membership(message):
        return

    # ویزارد پک
    s = sess(uid)
    if s.get("mode") == "pack_wizard":
        stage = s["pack_wizard"].get("stage")
        if stage == "ask_name":
            base = (message.text or "").strip().lower()
            
            # بررسی قوانین تلگرام برای نام پک
            if not re.match(r"^[a-z][a-z0-9_]{0,31}$", base):
                return await message.answer(
                    "❌ نام نامعتبر است!\n"
                    "قوانین:\n"
                    "• باید با حرف انگلیسی شروع شود\n"
                    "• فقط حروف کوچک انگلیسی، عدد و زیرخط\n"
                    "• حداکثر ۳۲ کاراکتر\n"
                    "مثال صحیح: my_stickers"
                )
            
            # چک کردن طول نهایی با پسوند ربات
            final_name = _normalize_shortname(base)
            if len(final_name) > 64:  # حد تلگرام
                return await message.answer(
                    "❌ نام خیلی طولانی است!\n"
                    f"نام نهایی: {final_name}\n"
                    "نام کوتاه‌تری انتخاب کنید."
                )
            
            u = user(uid)
            # عنوان را همان نام انگلیسی قرار بده
            title = base.replace('_', ' ').title()
            u["pack"] = {"title": title, "name": base, "created": False, "just_created_once": True}
            s["pack_wizard"] = {}
            s["mode"] = "menu"
            
            return await message.answer(
                f"✅ پک تنظیم شد!\n"
                f"نام: {final_name}\n"
                f"حالا از منو یکی را انتخاب کن:",
                reply_markup=main_menu_kb(is_admin=(uid == ADMIN_ID))
            )

    # ادامه منطق قبلی
    # پردازش درخواست‌های معلق ادمین
    if uid == ADMIN_ID and ADMIN_PENDING.get(ADMIN_ID):
        p = ADMIN_PENDING[ADMIN_ID]
        if p["action"] == "reset_quota":
            try:
                target = int((message.text or "").strip())
                if target in USERS:
                    USERS[target]["ai_used"] = 0
                    USERS[target]["day_start"] = _today_start_ts()
                    await message.answer(f"سهمیه کاربر {target} ریست شد ✅")
                else:
                    await message.answer("این کاربر هنوز در دیتای ربات نیست.")
            except Exception:
                await message.answer("ID معتبر بفرست.")
            ADMIN_PENDING.pop(ADMIN_ID, None)
            return
        if p["action"] == "pm_user":
            stage = p.get("stage")
            if stage == "ask_id":
                try:
                    ADMIN_PENDING[ADMIN_ID]["target"] = int((message.text or "").strip())
                    ADMIN_PENDING[ADMIN_ID]["stage"] = "ask_msg"
                    await message.answer("متن پیام را بفرست:")
                except Exception:
                    await message.answer("ID معتبر بفرست.")
                return
            elif stage == "ask_msg":
                target = p.get("target")
                try:
                    await message.bot.send_message(chat_id=target, text=f"[پیام ادمین]\n{message.text}")
                    await message.answer("ارسال شد ✅")
                except Exception as e:
                    await message.answer(f"ارسال نشد: {e}")
                ADMIN_PENDING.pop(ADMIN_ID, None)
                return

    mode = s.get("mode", "menu")

    # استیکر ساده
    if mode == "simple":
        st = s["simple"]
        if st["state"] == "ASK_TEXT" and message.text:
            st["text"] = message.text.strip()
            st["state"] = "ASK_BG"
            await message.answer("پس‌زمینه را انتخاب کن:", reply_markup=simple_bg_kb())
            return
        elif st["state"] == "WAIT_BG_PHOTO" and message.photo:
            largest = message.photo[-1]
            buf = BytesIO()
            await message.bot.download(largest, destination=buf)
            st["bg_mode"] = "photo"
            st["bg_photo"] = buf.getvalue()
            img = render_image(text=st["text"], position="center", font_key="Default", color_hex="#FFFFFF",
                               size_key="medium", bg_mode=st["bg_mode"], bg_photo=st["bg_photo"], as_webp=False)
            file_obj = BufferedInputFile(img, filename="preview.png")
            await message.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
            return
        else:
            if message.photo and st.get("state") == "ASK_BG":
                largest = message.photo[-1]
                buf = BytesIO()
                await message.bot.download(largest, destination=buf)
                st["bg_mode"] = "photo"
                st["bg_photo"] = buf.getvalue()
                img = render_image(text=st["text"], position="center", font_key="Default", color_hex="#FFFFFF",
                                   size_key="medium", bg_mode="photo", bg_photo=st["bg_photo"], as_webp=False)
                file_obj = BufferedInputFile(img, filename="preview.png")
                await message.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
                return
            elif message.video:
                # اگر ویدیو ارسال شد، راهنمایی کن که به بخش AI برود
                return await message.answer("برای ساخت استیکر ویدیویی، از بخش «استیکر هوش مصنوعی 🤖» استفاده کنید.")
            # اگر خارج از جریان چیزی فرستاد
            return await message.answer("از دکمه‌ها استفاده کن یا متن/عکس مناسب بفرست.")

    # استیکر هوش مصنوعی
    if mode == "ai":
        a = s["ai"]
        u = user(uid)
        is_admin = (uid == ADMIN_ID)
        left = _quota_left(u, is_admin)
        
        # دریافت ویدیو برای استیکر ویدیویی
        if a.get("video_mode") and a.get("video_data") is None and message.video:
            if left <= 0 and not is_admin:
                eta = _fmt_eta(_seconds_to_reset(u))
                return await message.answer(f"سهمیه امروز تمام شد. تمدید در: {eta}")
            
            try:
                # دانلود ویدیو
                buf = BytesIO()
                await message.bot.download(message.video, destination=buf)
                video_bytes = buf.getvalue()
                
                # تبدیل به WebM
                processed_video = process_video_to_webm(video_bytes)
                a["video_data"] = processed_video
                
                await message.answer("ویدیو دریافت شد! حالا متن رو بفرست ✍️")
                return
            except Exception as e:
                return await message.answer(f"خطا در پردازش ویدیو: {str(e)}")
        
        # دریافت متن
        if a["text"] is None and message.text:
            if left <= 0 and not is_admin:
                eta = _fmt_eta(_seconds_to_reset(u))
                return await message.answer(f"سهمیه امروز تمام شد. تمدید در: {eta}")
            
            a["text"] = message.text.strip()
            inferred = infer_from_text(a["text"])
            a.update(inferred)
            
            # اگر حالت ویدیویی است و ویدیو ندارد
            if a.get("video_mode") and not a.get("video_data"):
                return await message.answer("اول ویدیو رو ارسال کن 🎬")
            
            kb = InlineKeyboardBuilder()
            for label, val in [("بالا ⬆️", "top"), ("وسط ⚪️", "center"), ("پایین ⬇️", "bottom")]:
                kb.button(text=label, callback_data=f"ai:pos:{val}")
            kb.adjust(3)
            await message.answer("متن کجا قرار بگیرد؟", reply_markup=kb.as_markup())
            return
        
        # دریافت عکس پس‌زمینه (فقط برای حالت تصویری)
        if not a.get("video_mode") and a.get("bg") == "photo" and a.get("bg_photo") is None and message.photo:
            largest = message.photo[-1]
            buf = BytesIO()
            await message.bot.download(largest, destination=buf)
            a["bg_photo"] = buf.getvalue()
            if all(a.get(k) for k in ["text", "position", "font", "color", "size"]):
                await send_ai_preview(message, uid)
            else:
                await message.answer("ادامه تنظیمات را با دکمه‌ها انتخاب کن.")
            return

    # بازخورد (بعد از سوال نارضایتی)
    if s.get("await_feedback"):
        reason = (message.text or "").strip()
        s["await_feedback"] = False
        # ارسال برای ادمین (اختیاری)
        try:
            if uid != ADMIN_ID:
                await message.bot.send_message(chat_id=ADMIN_ID, text=f"بازخورد کاربر {uid}:\n{reason}")
        except Exception:
            pass
        return await message.answer("ممنون از بازخوردت 🙏", reply_markup=back_to_menu_kb(uid == ADMIN_ID))

    await message.answer("از منو یکی را انتخاب کن:", reply_markup=main_menu_kb(is_admin=(uid == ADMIN_ID)))

# ----- بازخورد و افزودن به پک -----
@router.callback_query(F.data == "rate:yes")
async def on_rate_yes(cb: CallbackQuery):
    await cb.message.answer("عالیه! می‌خوای به پک‌ات اضافه کنم؟", reply_markup=add_to_pack_kb())
    await cb.answer()

@router.callback_query(F.data == "rate:no")
async def on_rate_no(cb: CallbackQuery):
    sess(cb.from_user.id)["await_feedback"] = True
    await cb.message.answer("چه چیزی راضیت نکرد؟ لطفاً کوتاه توضیح بده:")
    await cb.answer()

@router.callback_query(F.data == "pack:skip")
async def on_pack_skip(cb: CallbackQuery):
    await cb.message.answer("باشه، اضافه نکردم. هر وقت خواستی از منو دوباره انتخاب کن.", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "pack:add")
async def on_pack_add(cb: CallbackQuery):
    uid = cb.from_user.id
    s = sess(uid)
    webp = s.get("last_sticker")
    video_webm = s.get("last_video_sticker")
    
    if not webp and not video_webm:
        await cb.answer("استیکری برای افزودن ندارم.", show_alert=True)
        return
    
    # اگر اطلاعات پک ناقص است، ویزارد را شروع کن
    if await need_pack_setup(uid):
        await start_pack_wizard(cb, uid)
        return await cb.answer("اول پک را تنظیم کن")
    
    if video_webm:
        # برای ویدیو استیکر، از تابع خاص استفاده کن
        msg = await _add_video_to_pack(cb.bot, uid, video_webm)
    else:
        # برای استیکر معمولی
        msg = await _add_to_pack(cb.bot, uid, webp)
    
    await cb.message.answer(msg, reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    await cb.answer()

# ----- پنل ادمین (بدون تغییرات خاص) -----
def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="آمار 📈", callback_data="admin:stats")
    kb.button(text="رأی‌ها 📊", callback_data="admin:votes")
    kb.button(text="ریست سهمیه کاربر 🔄", callback_data="admin:reset_one")
    kb.button(text="ریست همه سهمیه‌ها 🧹", callback_data="admin:reset_all")
    kb.button(text="ارسال پیام به کاربر ✉️", callback_data="admin:pm")
    kb.button(text=f"{'خاموش' if MAINTENANCE else 'روشن'} کردن نگهداری 🛠", callback_data="admin:toggle_maint")
    kb.adjust(2, 2, 2)
    return kb.as_markup()

@router.callback_query(F.data == "menu:admin")
async def on_admin(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("اجازه دسترسی ندارید", show_alert=True)
        return
    await cb.message.answer("پنل ادمین:", reply_markup=admin_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:stats")
async def admin_stats(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("No", show_alert=True)
    total_users = len(USERS)
    used_today = sum(1 for v in USERS.values() if v.get("ai_used", 0) > 0)
    votes_yes = sum(1 for v in USERS.values() if v.get("vote") == "yes")
    votes_no = sum(1 for v in USERS.values() if v.get("vote") == "no")
    await cb.message.answer(f"کاربران: {total_users}\nکاربرانی که امروز AI استفاده کردند: {used_today}\nرأی‌ها: بله {votes_yes} | خیر {votes_no}")
    await cb.answer()

@router.callback_query(F.data == "admin:votes")
async def admin_votes(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("No", show_alert=True)
    yes = [uid for uid, v in USERS.items() if v.get("vote") == "yes"]
    no = [uid for uid, v in USERS.items() if v.get("vote") == "no"]
    txt = f"بله: {len(yes)}\n{yes[:20]}\n\nخیر: {len(no)}\n{no[:20]}"
    await cb.message.answer(txt)
    await cb.answer()

@router.callback_query(F.data == "admin:reset_one")
async def admin_reset_one(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("No", show_alert=True)
    ADMIN_PENDING[ADMIN_ID] = {"action": "reset_quota"}
    await cb.message.answer("ID کاربر را بفرست تا سهمیه AI او ریست شود.")
    await cb.answer()

@router.callback_query(F.data == "admin:reset_all")
async def admin_reset_all(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("No", show_alert=True)
    for v in USERS.values():
        v["ai_used"] = 0
        v["day_start"] = _today_start_ts()
    await cb.message.answer("همه سهمیه‌ها ریست شد ✅")
    await cb.answer()

@router.callback_query(F.data == "admin:pm")
async def admin_pm(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("No", show_alert=True)
    ADMIN_PENDING[ADMIN_ID] = {"action": "pm_user", "stage": "ask_id"}
    await cb.message.answer("ID کاربر را بفرست:")
    await cb.answer()

@router.callback_query(F.data == "admin:toggle_maint")
async def admin_toggle_maint(cb: CallbackQuery):
    global MAINTENANCE
    if cb.from_user.id != ADMIN_ID:
        return await cb.answer("No", show_alert=True)
    MAINTENANCE = not MAINTENANCE
    await cb.message.answer(f"حالت نگهداری: {'فعال' if MAINTENANCE else 'غیرفعال'}")
    await cb.answer()

# ============ دستورات پایه و اجرا ============
async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="شروع"),
    ])

async def main():
    global BOT_USERNAME
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    me = await bot.get_me()
    BOT_USERNAME = me.username or "mybot"
    dp = Dispatcher()
    dp.include_router(router)
    await set_commands(bot)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print("deleteWebhook failed (ignored):", e)

    print("Bot is running. Press Ctrl+C to stop.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
