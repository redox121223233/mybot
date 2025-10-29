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

def _seconds_to_reset(u: Dict[str, Any]) -> int:
    _reset_daily_if_needed(u)
    now = int(datetime.now(timezone.utc).timestamp())
    end = int(u["day_start"]) + 86400
    return max(0, end - now)

def _fmt_eta(secs: int) -> str:
    h = secs // 3600
    m = (secs % 3600) // 60
    if h <= 0 and m <= 0:
        return "کمتر از 1 دقیقه"
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

# ============ توابع مدیرییت پک‌های کاربر ============
def get_user_packs(uid: int) -> List[Dict[str, str]]:
    """دریافت لیست پک‌های کاربر"""
    u = user(uid)
    return u.get("packs", [])

def add_user_pack(uid: int, pack_name: str, pack_short_name: str):
    """افزودن پک جدید به لیست پک‌های کاربر"""
    u = user(uid)
    packs = u.get("packs", [])
    
    for pack in packs:
        if pack["short_name"] == pack_short_name:
            return
    
    packs.append({
        "name": pack_name,
        "short_name": pack_short_name
    })
    u["packs"] = packs
    u["current_pack"] = pack_short_name

def set_current_pack(uid: int, pack_short_name: str):
    """تنظیم پک فعلی کاربر"""
    u = user(uid)
    u["current_pack"] = pack_short_name

def get_current_pack(uid: int) -> Optional[Dict[str, str]]:
    """دریافت پک فعلی کاربر"""
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

# ============ توابع بررسی عضویت در کانال ============
async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

async def require_channel_membership(message: Message, bot: Bot) -> bool:
    is_member = await check_channel_membership(bot, message.from_user.id)
    if not is_member:
        kb = InlineKeyboardBuilder()
        kb.button(text="عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        kb.button(text="بررسی عضویت", callback_data="check_membership")
        kb.adjust(1)

        await message.answer(
            f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.\n\n"
            "پس از عضویت، روی دکمه «بررسی عضویت» کلیک کنید.",
            reply_markup=kb.as_markup()
        )
        return False
    return True

# ============ کیبوردها ============
def main_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎨 استیکر ساده", callback_data="menu:simple")
    kb.button(text="🤖 استیکر هوشمند", callback_data="menu:ai")
    kb.button(text="🎮 بازی و سرگرمی", callback_data="games:menu")
    kb.button(text="📊 سهمیه امروز", callback_data="menu:quota")
    kb.button(text="📖 راهنما", callback_data="menu:help")
    kb.button(text="🆘 پشتیبانی", callback_data="menu:support")
    if is_admin:
        kb.button(text="👤 پنل ادمین", callback_data="menu:admin")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

def back_to_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 بازگشت به منو", callback_data="menu:home")
    if is_admin:
        kb.button(text="👤 پنل ادمین", callback_data="menu:admin")
    kb.adjust(1)
    return kb.as_markup()

# ============ روتر اصلی ============
router = Router()

@router.message(CommandStart())
async def on_start(message: Message, bot: Bot):
    if not await require_channel_membership(message, bot):
        return
        
    reset_mode(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "سلام! خوش آمدید\n"
        "🎨 ربات ساخت استیکر و بازی‌های سرگرمی\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu_kb(is_admin)
    )

@router.callback_query(F.data == "check_membership")
async def on_check_membership(cb: CallbackQuery, bot: Bot):
    is_member = await check_channel_membership(bot, cb.from_user.id)
    if is_member:
        await cb.message.answer(
            "عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.",
            reply_markup=main_menu_kb(cb.from_user.id == ADMIN_ID)
        )
    else:
        await cb.answer("شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
    await cb.answer()

@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery, bot: Bot):
    if not await check_channel_membership(bot, cb.from_user.id):
        return
        
    reset_mode(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    await cb.message.answer(
        "🏠 منوی اصلی:",
        reply_markup=main_menu_kb(is_admin)
    )
    await cb.answer()

@router.callback_query(F.data == "games:menu")
async def on_games_menu(cb: CallbackQuery, bot: Bot):
    if not await check_channel_membership(bot, cb.from_user.id):
        return
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 حدس کلمه", callback_data="game:word_guess")
    kb.button(text="🎲 عدد شانس", callback_data="game:lucky_number") 
    kb.button(text="🧩 معما", callback_data="game:riddle")
    kb.button(text="😂 جوک روز", callback_data="game:joke")
    kb.button(text="📚 اطلاعات جالب", callback_data="game:fun_fact")
    kb.button(text="🔙 بازگشت به منوی اصلی", callback_data="menu:home")
    kb.adjust(2, 2, 2)
    
    await cb.message.edit_text(
        "🎮 **منوی بازی و سرگرمی**\n\n"
        "یکی از بازی‌های زیر را انتخاب کنید:",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "game:lucky_number")
async def on_lucky_number(cb: CallbackQuery, bot: Bot):
    import random
    lucky_number = random.randint(1, 100)
    user_lucky = random.randint(1, 100)
    
    if lucky_number == user_lucky:
        result_text = "🎉 **شما برنده شدید!** 🎉\n\n"
        prize = random.choice(["🎁 جایزه ویژه", "💎 امتیاز دو برابر", "⭐ ستاره طلایی"])
        result_text += f"عدد شانس: {lucky_number}\n"
        result_text += f"عدد شما: {user_lucky}\n"
        result_text += f"🎁 {prize}"
    else:
        result_text = "😊 **امتحان دوباره!** 😊\n\n"
        result_text += f"عدد شانس: {lucky_number}\n"
        result_text += f"عدد شما: {user_lucky}\n"
        result_text += "فاصله شما با برد: " + str(abs(lucky_number - user_lucky))
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🎲 بازی دوباره", callback_data="game:lucky_number")
    kb.button(text="🔙 بازگشت", callback_data="games:menu")
    kb.adjust(2)
    
    await cb.message.edit_text(
        f"🎲 **بازی عدد شانس**\n\n"
        f"{result_text}\n\n"
        f"برای بازی دیگر گزینه مورد نظر را انتخاب کنید:",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "game:joke")
async def on_joke(cb: CallbackQuery, bot: Bot):
    import random
    
    jokes = [
        "چرا ریاضیات دان غمگین بود؟ چون خیلی مسائل داشت! 😄",
        "معلم به دانش‌آموز: چرا توی امتحان خواب بودی؟\nدانش‌آموز: چون ذهنم در حال استراحت بود! 😴",
        "یک روز گوجه به گوجه دیگر گفت: چرا قرمز شدی؟\nگفت: دیدم خیار سبز شده، خجالت کشیدم! 🍅😊",
        "چرا ماهی به پول نرسید؟ چون همیشه تو آب بود! 🐠💰",
        "مردم به دکتر گفتند: دکتر ما فراموشکار شدیم!\nدکتر گفت: کی؟\nمردم گفتند: چی؟\nدکتر گفت: کی؟ 🤔"
    ]
    
    joke = random.choice(jokes)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="😂 جوک دیگر", callback_data="game:joke")
    kb.button(text="🔙 بازگشت", callback_data="games:menu")
    kb.adjust(2)
    
    await cb.message.edit_text(
        f"😂 **جوک امروز** 😂\n\n"
        f"{joke}\n\n"
        f"خندیدنی بود؟ 😄",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "game:fun_fact")
async def on_fun_fact(cb: CallbackQuery, bot: Bot):
    import random
    
    fun_facts = [
        "🧠 مغز انسان حدود 2% از وزن بدن را تشکیل می‌دهد ولی 20% از اکسیژن را مصرف می‌کند!",
        "🌍 زمین تنها سیاره‌ای در منظومه شمسی است که به نام یک خدای گیرس گرفته نشده است!",
        "🐘 فیل‌ها تنها حیواناتی هستند که نمی‌توانند بپرند! (و البته نمی‌خواهند بپرند!)",
        "⏹️ زمان در سیاهچاله متوقف می‌شود!",
        "🍯 عسل فاسد نمی‌شود - در مقابر مصر با قدمت 3000 سال عسل قابل خورش پیدا شده است!",
        "🌙 ماه هر سال حدود 3.8 سانتی‌متر از زمین دور می‌شود!",
        "🐧 پنگوئن‌ها می‌توانند تا سرعت 35 کیلومتر در ساعت شنا کنند!",
        "🎵 موسیقی می‌تواند به کاهش درد و اضطراب کمک کند!",
        "🌈 رنگ قرمز در rainbow اولین رنگی است که چشم انسان در نوزادی تشخیص می‌دهد!",
        "⚡ صاعقه می‌تواند دمای 30000 درجه سانتی‌گراد داشته باشد - 5 برابر دمای سطح خورشید!"
    ]
    
    fact = random.choice(fun_facts)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📚 اطلاعات دیگر", callback_data="game:fun_fact")
    kb.button(text="🔙 بازگشت", callback_data="games:menu")
    kb.adjust(2)
    
    await cb.message.edit_text(
        f"📚 **اطلاعات جالب امروز** 📚\n\n"
        f"{fact}\n\n"
        f"جالب نبود؟ 🤓✨",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "game:riddle")
async def on_riddle(cb: CallbackQuery, bot: Bot):
    import random
    
    riddles = [
        {'question': 'چه چیزی همیشه جلو می‌رود ولی هرگز به جایی نمی‌رسد؟', 'answer': 'زمان'},
        {'question': 'چه چیزی دهان دارد ولی صحبت نمی‌کند؟', 'answer': 'رودخانه'},
        {'question': 'چه چیزی سر دارد ولی گردن ندارد؟', 'answer': 'سکه'},
        {'question': 'چه چیزی می‌تواند پرواز کند ولی بال ندارد؟', 'answer': 'ابر'},
        {'question': 'چه چیزی شب‌ها می‌خوابد ولی روزها بیدار است؟', 'answer': 'ستاره'}
    ]
    
    riddle = random.choice(riddles)
    uid = cb.from_user.id
    
    SESSIONS[uid]['riddle'] = riddle
    
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 پاسخم را بگویم", callback_data="riddle_answer")
    kb.button(text="🔁 معمای دیگر", callback_data="game:riddle")
    kb.button(text="🔙 بازگشت", callback_data="games:menu")
    kb.adjust(1, 2)
    
    await cb.message.edit_text(
        f"🧩 **معمای امروز** 🧩\n\n"
        f"❓ {riddle['question']}\n\n"
        f"به فکر باشید... 😊",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "riddle_answer")
async def on_riddle_answer(cb: CallbackQuery, bot: Bot):
    uid = cb.from_user.id
    
    if 'riddle' not in SESSIONS[uid]:
        await cb.answer("معمای فعالی وجود ندارد!", show_alert=True)
        return
    
    riddle = SESSIONS[uid]['riddle']
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🧩 معمای دیگر", callback_data="game:riddle")
    kb.button(text="🔙 بازگشت", callback_data="games:menu")
    kb.adjust(2)
    
    await cb.message.edit_text(
        f"🧩 **پاسخ معما** 🧩\n\n"
        f"❓ {riddle['question']}\n\n"
        f"💡 **پاسخ:** {riddle['answer']}\n\n"
        f"چقدر هوشمند بودید؟ 🧠✨",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "game:word_guess")
async def on_word_guess_start(cb: CallbackQuery, bot: Bot):
    kb = InlineKeyboardBuilder()
    kb.button(text="😊 آسان", callback_data="word_guess:easy")
    kb.button(text="😐 متوسط", callback_data="word_guess:medium")
    kb.button(text="😈 سخت", callback_data="word_guess:hard")
    kb.button(text="🔙 بازگشت", callback_data="games:menu")
    kb.adjust(2, 2)
    
    await cb.message.edit_text(
        "🎯 **بازی حدس کلمه**\n\n"
        "سختی بازی را انتخاب کنید:",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("word_guess:"))
async def on_word_guess_difficulty(cb: CallbackQuery, bot: Bot):
    import random
    
    difficulty = cb.data.split(":")[1]
    uid = cb.from_user.id
    
    word_games = {
        'easy': [
            {'word': 'گربه', 'hint': 'حیوان خانگی، موش‌گیر', 'category': 'حیوانات'},
            {'word': 'ماشین', 'hint': 'وسیله نقلیه، چهار چرخ', 'category': 'وسایل نقلیه'},
            {'word': 'سیب', 'hint': 'میوه، قرمز یا سبز', 'category': 'میوه‌ها'},
        ],
        'medium': [
            {'word': 'پایتخت', 'hint': 'مرکز یک کشور', 'category': 'جغرافیا'},
            {'word': 'کامپیوتر', 'hint': 'دستگاه الکترونیکی هوشمند', 'category': 'تکنولوژی'},
            {'word': 'دوچرخه', 'hint': 'وسیله نقلیه بدون موتور، دو چرخ', 'category': 'وسایل نقلیه'},
        ],
        'hard': [
            {'word': 'فلسفه', 'hint': 'علم تفکر و اندیشه', 'category': 'علوم'},
            {'word': 'تکنولوژی', 'hint': 'دانش کاربردی علمی', 'category': 'علوم'},
            {'word': 'روانشناسی', 'hint': 'علم مطالعه رفتار و ذهن', 'category': 'علوم'},
        ]
    }
    
    word_data = random.choice(word_games[difficulty])
    word = word_data['word']
    hint = word_data['hint']
    category = word_data['category']
    
    SESSIONS[uid]['word_guess'] = {
        'word': word,
        'hint': hint,
        'category': category,
        'difficulty': difficulty,
        'attempts_left': 6,
        'guessed_letters': set(),
        'wrong_guesses': []
    }
    
    display_word = ''.join(['_' if char != ' ' else ' ' for char in word])
    difficulty_emoji = {'easy': '😊', 'medium': '😐', 'hard': '😈'}
    
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 حدس بزنم", callback_data="guess_input")
    kb.button(text="🔁 انصراف", callback_data="games:menu")
    kb.adjust(2)
    
    await cb.message.edit_text(
        f"🎯 **حدس کلمه - {difficulty_emoji[difficulty]}**\n\n"
        f"📂 دسته: {category}\n"
        f"💭 راهنمایی: {hint}\n"
        f"🎯 کلمه: {display_word}\n"
        f"❤️ فرصت باقی‌مانده: {SESSIONS[uid]['word_guess']['attempts_left']}\n\n"
        f"کلمه مورد نظر را حدس بزنید:",
        reply_markup=kb.as_markup()
    )
    await cb.answer()

@router.callback_query(F.data == "guess_input")
async def on_guess_input(cb: CallbackQuery, bot: Bot):
    await cb.message.edit_text(
        "💬 **حدس کلمه**\n\n"
        "کلمه مورد نظر را تایپ کنید:",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:help")
async def on_help(cb: CallbackQuery, bot: Bot):
    if not await check_channel_membership(bot, cb.from_user.id):
        return
        
    help_text = (
        "📖 **راهنمای ربات**\n\n"
        "🎨 **قابلیت‌های اصلی:**\n"
        "• ساخت استیکر ساده - ایجاد استیکر با تنظیمات سریع\n"
        "• ساخت استیکر هوشمند - ایجاد استیکر با تنظیمات پیشرفته\n"
        "🎮 **بازی‌ها و سرگرمی:**\n"
        "• حدس کلمه - بازی فکری با سه سطح سختی\n"
        "• عدد شانس - بازی شانس و اعداد\n"
        "• معما - معما‌های جالب و هوشمندانه\n"
        "• جوک روز - جوک‌های خنده‌دار روزانه\n"
        "• اطلاعات جالب - دانستنی‌های علمی و جذاب\n"
        "📊 **سایر امکانات:**\n"
        "• سهمیه روزانه - محدودیت استفاده روزانه\n"
        "• پشتیبانی - ارتباط با ادمین"
    )
    await cb.message.answer(help_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:support")
async def on_support(cb: CallbackQuery, bot: Bot):
    if not await check_channel_membership(bot, cb.from_user.id):
        return
        
    await cb.message.answer(
        f"🆘 **پشتیبانی**\n\n"
        f"برای ارتباط با پشتیبانی:\n{SUPPORT_USERNAME}",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:quota")
async def on_quota(cb: CallbackQuery, bot: Bot):
    if not await check_channel_membership(bot, cb.from_user.id):
        return
        
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    quota_txt = "نامحدود" if is_admin else f"{left} از {u.get('daily_limit', DAILY_LIMIT)}"
    await cb.message.answer(
        f"📊 **سهمیه امروز:** {quota_txt}",
        reply_markup=back_to_menu_kb(is_admin)
    )
    await cb.answer()

@router.message()
async def on_message(message: Message, bot: Bot):
    uid = message.from_user.id
    s = sess(uid)
    is_admin = (uid == ADMIN_ID)
    
    if not await require_channel_membership(message, bot):
        return

    # بررسی حدس کلمه
    if 'word_guess' in s and message.text and message.text.strip():
        game = s['word_guess']
        guessed_word = message.text.strip()
        
        if guessed_word == game['word']:
            del s['word_guess']
            await message.answer(
                f"🎉 **تبریک! شما برنده شدید!** 🎉\n\n"
                f"کلمه: {game['word']}\n"
                f"🏆 امتیاز شما: +{10 * len(game['word'])}\n\n"
                f"برای بازی دیگر منوی بازی را انتخاب کنید:",
                reply_markup=main_menu_kb(is_admin)
            )
            return
        else:
            game['attempts_left'] -= 1
            if game['attempts_left'] <= 0:
                del s['word_guess']
                await message.answer(
                    f"😢 **متاسفانه شما باختید!** 😢\n\n"
                    f"کلمه: {game['word']}\n\n"
                    f"برای بازی دیگر منوی بازی را انتخاب کنید:",
                    reply_markup=main_menu_kb(is_admin)
                )
                return
            else:
                display_word = ''.join(['_' if char != ' ' else ' ' for char in game['word']])
                difficulty_emoji = {'easy': '😊', 'medium': '😐', 'hard': '😈'}
                
                kb = InlineKeyboardBuilder()
                kb.button(text="💬 حدس بزنم", callback_data="guess_input")
                kb.button(text="🔁 انصراف", callback_data="games:menu")
                kb.adjust(2)
                
                await message.answer(
                    f"🎯 **حدس کلمه - {difficulty_emoji[game['difficulty']}**\n\n"
                    f"📂 دسته: {game['category']}\n"
                    f"💭 راهنمایی: {game['hint']}\n"
                    f"🎯 کلمه: {display_word}\n"
                    f"❤️ فرصت باقی‌مانده: {game['attempts_left']}\n\n"
                    f"کلمه مورد نظر را حدس بزنید:",
                    reply_markup=kb.as_markup()
                )
                return

    # پاسخ پیش‌فرض برای پیام‌های ناشناخته
    await message.answer(
        "❓ پیام ناشناخته است. لطفاً از منوی اصلی استفاده کنید:",
        reply_markup=main_menu_kb(is_admin)
    )

# ================ تابع اصلی ================
async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    dp.include_router(router)
    
    print("🤖 ربات با موفقیت راه‌اندازی شد!")
    print("🎮 ربات ساخت استیکر + بازی‌های سرگرمی")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())