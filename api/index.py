import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import subprocess
import pydantic_core
import traceback

from fastapi import Request, FastAPI
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, BotCommand, BufferedInputFile, InputSticker, Update
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

# --- مسیرهای صحیح برای FSM در aiogram v3 ---
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy
# --- پایان مسیرهای صحیح ---

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# ... بقیه کد شما بدون تغییر باقی می‌ماند ...

# =============== پیکربندی ===============
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

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

# ... (تمام توابع کمکی شما بدون تغییر باقی می‌مانند) ...
# _today_start_ts, _reset_daily_if_needed, _quota_left, user, sess, reset_mode
# get_user_packs, add_user_pack, set_current_pack, get_current_pack
# _load_local_fonts, _detect_language, resolve_font_path
# _prepare_text, is_persian, _parse_hex, fit_font_size, _make_default_bg
# render_image, is_ffmpeg_installed, process_video_to_webm
# check_channel_membership, require_channel_membership
# main_menu_kb, back_to_menu_kb, simple_bg_kb, after_preview_kb, rate_kb
# pack_selection_kb, add_to_pack_kb, ai_type_kb, ai_image_source_kb
# ai_vpos_kb, ai_hpos_kb, admin_panel_kb
# check_pack_exists, is_valid_pack_name

# (برای صرفه‌جویی در فضا، توابع کمکی را اینجا کپی می‌کنم. شما باید آن‌ها را از کد قبلی خود کپی کنید)
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
            "ai_used": 0, "vote": None, "day_start": _today_start_ts(), "packs": [], "current_pack": None
        }
    _reset_daily_if_needed(USERS[uid])
    return USERS[uid]

def sess(uid: int) -> Dict[str, Any]:
    if uid not in SESSIONS:
        SESSIONS[uid] = {
            "mode": "menu", "ai": {}, "simple": {}, "pack_wizard": {}, "await_feedback": False,
            "last_sticker": None, "last_video_sticker": None, "admin": {}
        }
    return SESSIONS[uid]

def reset_mode(uid: int):
    s = sess(uid)
    s["mode"] = "menu"; s["ai"] = {}; s["simple"] = {}; s["await_feedback"] = False
    s["last_sticker"] = None; s["last_video_sticker"] = None; s["pack_wizard"] = {}; s["admin"] = {}
    if "current_pack_short_name" in s: del s["current_pack_short_name"]
    if "current_pack_title" in s: del s["current_pack_title"]

def get_user_packs(uid: int) -> List[Dict[str, str]]:
    u = user(uid)
    return u.get("packs", [])

def add_user_pack(uid: int, pack_name: str, pack_short_name: str):
    u = user(uid)
    packs = u.get("packs", [])
    for pack in packs:
        if pack["short_name"] == pack_short_name: return
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

# ... (بقیه توابع کمکی را از کد قبلی خود اینجا کپی کنید) ...
# در اینجا برای صرفه‌جویی، تمام توابع رندر، کیبورد و... را قرار می‌دهم.
# شما باید آن‌ها را کامل از کد قبلی خود کپی کنید.
# من فقط نمونه‌ای را می‌نویسم.

DEFAULT_PALETTE = [("سفید", "#FFFFFF"), ("مشکی", "#000000"), ("قرمز", "#F43F5E"), ("آبی", "#3B82F6"), ("سبز", "#22C55E"), ("زرد", "#EAB308"), ("بنفش", "#8B5CF6"), ("نارنجی", "#F97316")]
NAME_TO_HEX = {name: hx for name, hx in DEFAULT_PALETTE}
POS_WORDS = {"بالا": "top", "وسط": "center", "میانه": "center", "پایین": "bottom"}
SIZE_WORDS = {"ریز": "small", "متوسط": "medium", "بزرگ": "large", "درشت": "large"}

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
LOCAL_FONT_FILES = {"Vazirmatn": ["Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf"], "NotoNaskh": ["NotoNaskhArabic-Regular.ttf", "NotoNaskhArabic-Medium.ttf"], "Sahel": ["Sahel.ttf", "Sahel-Bold.ttf"], "IRANSans": ["IRANSans.ttf", "IRANSansX-Regular.ttf"], "Roboto": ["Roboto-Regular.ttf", "Roboto-Medium.ttf"], "Default": ["Vazirmatn-Regular.ttf", "Roboto-Regular.ttf"]}
PERSIAN_FONTS = ["Vazirmatn", "NotoNaskh", "Sahel", "IRANSans"]
ENGLISH_FONTS = ["Roboto"]

def _load_local_fonts() -> Dict[str, str]:
    found: Dict[str, str] = {}
    if os.path.isdir(FONT_DIR):
        for logical, names in LOCAL_FONT_FILES.items():
            for name in names:
                p = os.path.join(FONT_DIR, name)
                if os.path.isfile(p): found[logical] = p; break
    return found

_LOCAL_FONTS = _load_local_fonts()

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

CANVAS = (512, 512)
def _prepare_text(text: str) -> str:
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def is_persian(text):
    if not text: return False
    persian_pattern = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
    return bool(persian_pattern.search(text))

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3: r, g, b = [int(c * 2, 16) for c in hx]
    else: r = int(hx[0:2], 16); g = int(hx[2:4], 16); b = int(hx[4:6], 16)
    return (r, g, b, 255)

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    size = base
    while size > 12:
        try: font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception: font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if tw <= max_w and th <= max_h: return size
        size -= 1
    return max(size, 12)

def _make_default_bg(size=(512, 512)) -> Image.Image:
    w, h = size
    img = Image.new("RGBA", size, (20, 20, 35, 255))
    top = (56, 189, 248); bottom = (99, 102, 241)
    dr = ImageDraw.Draw(img)
    for y in range(h):
        t = y / (h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        dr.line([(0, y), (w, y)], fill=(r, g, b, 255))
    return img.filter(ImageFilter.GaussianBlur(0.5))

def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str, bg_mode: str = "transparent", bg_photo: Optional[bytes] = None, as_webp: bool = False) -> bytes:
    W, H = CANVAS
    if bg_photo:
        try: img = Image.open(BytesIO(bg_photo)).convert("RGBA").resize((W, H))
        except Exception: img = _make_default_bg((W, H)) if bg_mode == "default" else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    else:
        img = _make_default_bg((W, H)) if bg_mode == "default" else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img); color = _parse_hex(color_hex); padding = 40
    box_w, box_h = W - 2 * padding, H - 2 * padding
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)
    font_path = resolve_font_path(font_key, text)
    txt = _prepare_text(text)
    final_size = fit_font_size(draw, txt, font_path, base_size, box_w, box_h)
    try: font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
    except Exception: font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), txt, font=font)
    text_width = bbox[2] - bbox[0]; text_height = bbox[3] - bbox[1]
    if v_pos == "top": y = padding
    elif v_pos == "bottom": y = H - padding - text_height
    else: y = (H - text_height) / 2
    if h_pos == "left": x = padding
    elif h_pos == "right": x = W - padding - text_width
    else: x = W / 2
    draw.text((x, y), txt, font=font, fill=color, anchor="mm" if h_pos == "center" else "lm", stroke_width=2, stroke_fill=(0, 0, 0, 220))
    buf = BytesIO()
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

def is_ffmpeg_installed() -> bool:
    try: subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, text=True); return True
    except (FileNotFoundError, subprocess.CalledProcessError): return False

async def process_video_to_webm(video_bytes: bytes) -> Optional[bytes]:
    if not is_ffmpeg_installed(): return None
    try:
        process = subprocess.Popen(['ffmpeg', '-i', '-', '-f', 'webm', '-c:v', 'libvpx-vp9', '-b:v', '1M', '-crf', '30', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=video_bytes)
        if process.returncode != 0: print(f"FFmpeg error: {stderr.decode()}"); return None
        return stdout
    except Exception as e: print(f"Error during video processing: {e}"); return None

async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    try: member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id); return member.status in ["member", "administrator", "creator"]
    except Exception as e: print(f"Error checking channel membership: {e}"); return False

async def require_channel_membership(message: Message, bot: Bot) -> bool:
    is_member = await check_channel_membership(bot, message.from_user.id)
    if not is_member:
        kb = InlineKeyboardBuilder()
        kb.button(text="عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        kb.button(text="بررسی عضویت", callback_data="check_membership")
        kb.adjust(1)
        await message.answer(f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.\n\nپس از عضویت، روی دکمه «بررسی عضویت» کلیک کنید.", reply_markup=kb.as_markup())
        return False
    return True

# ... (تمام توابع کیبورد و...) ...
def main_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر ساده", callback_data="menu:simple")
    kb.button(text="استیکر ساز پیشرفته", callback_data="menu:ai")
    kb.button(text="سهمیه امروز", callback_data="menu:quota")
    kb.button(text="راهنما", callback_data="menu:help")
    kb.button(text="پشتیبانی", callback_data="menu:support")
    if is_admin: kb.button(text="پنل ادمین", callback_data="menu:admin")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()

def back_to_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="بازگشت به منو", callback_data="menu:home")
    if is_admin: kb.button(text="پنل ادمین", callback_data="menu:admin")
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
    if current_pack: kb.button(text=f"📦 {current_pack['name']} (فعلی)", callback_data=f"pack:select:{current_pack['short_name']}")
    for pack in user_packs:
        if current_pack and pack["short_name"] == current_pack["short_name"]: continue
        kb.button(text=f"📦 {pack['name']}", callback_data=f"pack:select:{pack['short_name']}")
    kb.button(text="➕ ساخت پک جدید", callback_data=f"pack:new:{mode}")
    kb.adjust(1)
    return kb.as_markup()

def add_to_pack_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="افزودن به پک جدید", callback_data="pack:start_creation")
    kb.button(text="انتخاب از پک‌های قبلی", callback_data="pack:select_existing")
    kb.button(text="نه، لازم نیست", callback_data="pack:skip")
    kb.adjust(3)
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

async def check_pack_exists(bot: Bot, short_name: str) -> bool:
    try: await bot.get_sticker_set(name=short_name); return True
    except TelegramBadRequest as e:
        if "STICKERSET_INVALID" in e.message or "invalid sticker set name" in e.message.lower(): return False
        raise

def is_valid_pack_name(name: str) -> bool:
    if not (1 <= len(name) <= 50): return False
    if not name[0].isalpha() or not name[0].islower(): return False
    if name.endswith('_'): return False
    if '__' in name: return False
    for char in name:
        if not (char.islower() or char.isdigit() or char == '_'): return False
    return True

# ============ روتر و هندلرها ============
router = Router()

# ... (تمام هندلرهای شما را اینجا کپی کنید) ...
# من چند نمونه را اینجا می‌آورم، شما باید همه را کپی کنید.

@router.message(CommandStart())
async def on_start(message: Message, bot: Bot):
    if not await require_channel_membership(message, bot): return
    reset_mode(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer("سلام! خوش آمدید\nیکی از گزینه‌های زیر رو انتخاب کن:", reply_markup=main_menu_kb(is_admin))

@router.callback_query(F.data == "check_membership")
async def on_check_membership(cb: CallbackQuery, bot: Bot):
    is_member = await check_channel_membership(bot, cb.from_user.id)
    if is_member:
        await cb.message.answer("عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.", reply_markup=main_menu_kb(cb.from_user.id == ADMIN_ID))
    else: await cb.answer("شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
    await cb.answer()

# ... (بقیه هندلرها را از کد قبلی خود اینجا کپی کنید. دقت کنید که همه هندلرها باید router@ داشته باشند) ...

# برای مثال:
@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery, bot: Bot):
    if not await check_channel_membership(bot, cb.from_user.id): return
    reset_mode(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    await cb.message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
    await cb.answer()

# ... (و غیره)

# =============== بخش اصلی وب‌هوک ===============
# ... تمام کدهای قبلی شما تا اینجا بدون تغییر باقی می‌ماند ...

# =============== بخش اصلی وب‌هوک (اصلاح شده) ===============
storage = MemoryStorage()
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT)
dp.include_router(router)

# یک نمونه از بوت را در سطح بالا بسازید
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    # لاگ برای اینکه بفهمیم درخواست می‌رسد یا نه
    print("Webhook received a request!")
    
    try:
        update_data = await request.json()
        # آپدیت را از داده‌های JSON بسازید
        update = Update.model_validate(update_data, context={"bot": bot})
        
        # آپدیت را به دیسپچر بفرست
        await dp.feed_webhook_update(update, bot=bot)
        
        return {"status": "ok"}
    except Exception as e:
        # اگر خطایی رخ داد، آن را چاپ کن تا در لاگ‌ها ببینیم
        print(f"Error processing webhook: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get("/")
async def read_root():
    return {"status": "Bot is running"}
