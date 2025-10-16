import os
import re
import json
from io import BytesIO
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputSticker
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# --- پیکربندی ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در متغیرهای محیطی تنظیم کنید.")
ADMIN_ID = 6053579919
DAILY_LIMIT = 5

# --- مدیریت کاربران با فایل JSON ---
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

def load_users() -> Dict[int, Dict[str, Any]]:
    """اطلاعات کاربران را از فایل JSON می‌خواند"""
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_users(users_data: Dict[int, Dict[str, Any]]):
    """اطلاعات کاربران را در فایل JSON ذخیره می‌کند"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)

def get_user(uid: int) -> Dict[str, Any]:
    """اطلاعات یک کاربر خاص را گرفته و در صورت نیاز آپدیت می‌کند"""
    users = load_users()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    today_start_ts = int(datetime(now_ts.year, now_ts.month, now_ts.day, tzinfo=timezone.utc).timestamp())

    if uid not in users:
        users[uid] = {"ai_used": 0, "day_start_ts": today_start_ts}
    
    # ریست سهمیه روزانه
    if users[uid].get("day_start_ts", 0) < today_start_ts:
        users[uid]["ai_used"] = 0
        users[uid]["day_start_ts"] = today_start_ts
    
    save_users(users)
    return users[uid]

def increment_ai_usage(uid: int):
    """یک واحد به استفاده هوش مصنوعی کاربر اضافه می‌کند"""
    users = load_users()
    if uid in users:
        users[uid]["ai_used"] += 1
        save_users(users)

# --- فونت‌ها ---
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
LOCAL_FONT_FILES = {"Vazirmatn": ["Vazirmatn-Regular.ttf"], "Default": ["Vazirmatn-Regular.ttf"]}

def _load_local_fonts() -> Dict[str, str]:
    found = {}
    if os.path.isdir(FONT_DIR):
        for logical, names in LOCAL_FONT_FILES.items():
            for name in names:
                p = os.path.join(FONT_DIR, name)
                if os.path.isfile(p):
                    found[logical] = p
                    break
    return found

_LOCAL_FONTS = _load_local_fonts()
DEFAULT_FONT_PATH = _LOCAL_FONTS.get("Default")

# --- توابع رندر ---
CANVAS = (512, 512)

def _prepare_text(text: str) -> str:
    if not text: return ""
    return get_display(arabic_reshaper.reshape(text))

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3: r, g, b = [int(c * 2, 16) for c in hx]
    else: r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
    return (r, g, b, 255)

def render_image(text: str, v_pos: str, h_pos: str, color_hex: str, size_key: str, bg_photo: Optional[bytes] = None) -> bytes:
    W, H = CANVAS
    if bg_photo:
        try:
            img = Image.open(BytesIO(bg_photo)).convert("RGBA").resize((W, H))
        except Exception:
            img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)
    color = _parse_hex(color_hex)
    padding = 40
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)
    
    txt = _prepare_text(text)
    try:
        font = ImageFont.truetype(DEFAULT_FONT_PATH, size=base_size)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), txt, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    if v_pos == "top": y = padding
    elif v_pos == "bottom": y = H - padding - text_height
    else: y = (H - text_height) / 2

    if h_pos == "left": x, anchor = padding, "ra"
    elif h_pos == "right": x, anchor = W - padding, "la"
    else: x, anchor = W / 2, "ma"
    
    draw.text((x, y), txt, font=font, fill=color, anchor=anchor, stroke_width=2, stroke_fill=(0, 0, 0, 220))
    
    buf = BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()

# --- کیبوردها ---
def main_menu_kb(is_admin=False):
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر ساده 🎄", callback_data="menu:simple")
    kb.button(text="استیکر هوش مصنوعی 🤖", callback_data="menu:ai")
    kb.button(text="سهمیه ⏳", callback_data="menu:quota")
    if is_admin: kb.button(text="ساخت پک 📦", callback_data="pack:start")
    kb.adjust(2, 1)
    return kb.as_markup()

def back_to_menu_kb(is_admin=False):
    kb = InlineKeyboardBuilder()
    kb.button(text="بازگشت به منو ↩️", callback_data="menu:home")
    return kb.as_markup()

def simple_bg_kb(text: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="شفاف ♻️", callback_data=f"simple:bg:transparent:{text}")
    kb.button(text="پیش‌فرض 🎨", callback_data=f"simple:bg:default:{text}")
    kb.button(text="ارسال عکس 🖼️", callback_data=f"simple:bg:photo_prompt:{text}")
    kb.adjust(3)
    return kb.as_markup()

def ai_vpos_kb(text: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="بالا ⬆️", callback_data=f"ai:vpos:top:{text}")
    kb.button(text="وسط ⚪️", callback_data=f"ai:vpos:center:{text}")
    kb.button(text="پایین ⬇️", callback_data=f"ai:vpos:bottom:{text}")
    kb.adjust(3)
    return kb.as_markup()

def ai_hpos_kb(text: str, v_pos: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="چپ ⬅️", callback_data=f"ai:hpos:left:{text}:{v_pos}")
    kb.button(text="وسط ⚪️", callback_data=f"ai:hpos:center:{text}:{v_pos}")
    kb.button(text="راست ➡️", callback_data=f"ai:hpos:right:{text}:{v_pos}")
    kb.adjust(3)
    return kb.as_markup()

def ai_color_kb(text: str, v_pos: str, h_pos: str):
    kb = InlineKeyboardBuilder()
    colors = {"سفید": "#FFFFFF", "مشکی": "#000000", "قرمز": "#F43F5E", "آبی": "#3B82F6"}
    for name, hx in colors.items():
        kb.button(text=name, callback_data=f"ai:color:{hx}:{text}:{v_pos}:{h_pos}")
    kb.adjust(2)
    return kb.as_markup()

def ai_size_kb(text: str, v_pos: str, h_pos: str, color: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="کوچک", callback_data=f"ai:size:small:{text}:{v_pos}:{h_pos}:{color}")
    kb.button(text="متوسط", callback_data=f"ai:size:medium:{text}:{v_pos}:{h_pos}:{color}")
    kb.button(text="بزرگ", callback_data=f"ai:size:large:{text}:{v_pos}:{h_pos}:{color}")
    kb.adjust(3)
    return kb.as_markup()

# --- روتر و هندلرها ---
router = Router()

@router.message(CommandStart())
async def on_start(message: Message):
    is_admin = message.from_user.id == ADMIN_ID
    await message.answer("سلام! خوش آمدید 🎉\nیکی از گزینه‌های زیر رو انتخاب کن:", reply_markup=main_menu_kb(is_admin))

@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery):
    is_admin = cb.from_user.id == ADMIN_ID
    await cb.message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
    await cb.answer()

@router.callback_query(F.data == "menu:quota")
async def on_quota(cb: CallbackQuery):
    user_data = get_user(cb.from_user.id)
    is_admin = cb.from_user.id == ADMIN_ID
    left = DAILY_LIMIT - user_data.get("ai_used", 0) if not is_admin else 999
    await cb.message.answer(f"سهمیه امروز: {left} از {DAILY_LIMIT}", reply_markup=back_to_menu_kb(is_admin))
    await cb.answer()

@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery):
    await cb.message.answer("متن استیکر ساده رو بفرست:", reply_markup=back_to_menu_kb())
    await cb.answer()

@router.callback_query(F.data == "menu:ai")
async def on_ai(cb: CallbackQuery):
    user_data = get_user(cb.from_user.id)
    is_admin = cb.from_user.id == ADMIN_ID
    if not is_admin and user_data.get("ai_used", 0) >= DAILY_LIMIT:
        await cb.message.answer("سهمیه امروز تمام شد! فردا دوباره امتحان کن.", reply_markup=back_to_menu_kb())
        await cb.answer()
        return
    await cb.message.answer("متن استیکر هوش مصنوعی رو بفرست:", reply_markup=back_to_menu_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("simple:bg:"))
async def on_simple_bg(cb: CallbackQuery):
    try:
        _, bg_type, text = cb.data.split(":", 2)
        if bg_type == "photo_prompt":
            await cb.message.answer("عکس مورد نظر را بفرستید:", reply_markup=back_to_menu_kb())
            await cb.answer()
            return
        
        img = render_image(text, v_pos="center", h_pos="center", color_hex="#FFFFFF", size_key="medium")
        await cb.message.answer_sticker(BufferedInputFile(img, "sticker.webp"))
        await cb.message.answer("استیکر شما آماده است!", reply_markup=back_to_menu_kb())
    except Exception:
        await cb.message.answer("خطایی رخ داد. لطفاً دوباره از منو شروع کنید.", reply_markup=main_menu_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ai:"))
async def on_ai_flow(cb: CallbackQuery):
    try:
        parts = cb.data.split(":")
        action = parts[1]
        
        if action == "vpos":
            _, _, v_pos, text = parts
            await cb.message.answer("موقعیت افقی را انتخاب کنید:", reply_markup=ai_hpos_kb(text, v_pos))
        elif action == "hpos":
            _, _, h_pos, text, v_pos = parts
            await cb.message.answer("رنگ متن را انتخاب کنید:", reply_markup=ai_color_kb(text, v_pos, h_pos))
        elif action == "color":
            _, _, color, text, v_pos, h_pos = parts
            await cb.message.answer("اندازه فونت را انتخاب کنید:", reply_markup=ai_size_kb(text, v_pos, h_pos, color))
        elif action == "size":
            _, _, size, text, v_pos, h_pos, color = parts
            img = render_image(text, v_pos, h_pos, color, size)
            await cb.message.answer_sticker(BufferedInputFile(img, "sticker.webp"))
            await cb.message.answer("استیکر شما آماده است!", reply_markup=back_to_menu_kb())
            increment_ai_usage(cb.from_user.id)
    except Exception:
        await cb.message.answer("خطایی رخ داد. لطفاً دوباره از منو شروع کنید.", reply_markup=main_menu_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("pack:"))
async def on_pack_flow(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("شما دسترسی به این بخش را ندارید.", show_alert=True)
        return
    
    action = cb.data.split(":")[1]
    if action == "start":
        await cb.message.answer("نام پک استیکر را انگلیسی و بدون فاصله ارسال کنید:", reply_markup=back_to_menu_kb(True))
    await cb.answer()

@router.message()
async def on_message(message: Message):
    uid = message.from_user.id
    is_admin = uid == ADMIN_ID

    # Handle pack creation for admin
    if is_admin and message.text and message.text.startswith("/createpack"):
        pack_name = message.text.replace("/createpack", "").strip()
        if pack_name:
            # In a real scenario, you'd ask for the first sticker text here
            # For simplicity, let's just create an empty pack
            try:
                await message.bot.create_new_sticker_set(user_id=uid, name=pack_name, title=pack_name, stickers=[], sticker_type='regular', sticker_format='static')
                await message.answer(f"✅ پک `{pack_name}` با موفقیت ساخته شد.")
            except Exception as e:
                await message.answer(f"خطا در ساخت پک: {e}")
        else:
            await message.answer("لطفاً نام پک را ارسال کنید. مثال: /createpack MyPack")
        return

    # Handle photo for background
    if message.photo:
        # This requires a more complex state management, which is tricky on Vercel.
        # For now, we'll just acknowledge it.
        await message.answer("عکس دریافت شد. لطفاً متن استیکر را از منوی مربوطه ارسال کنید.")
        return

    # Handle text for sticker creation
    if message.text:
        if "متن استیکر ساده" in message.reply_to_message.text if message.reply_to_message else False:
            await message.answer("پس‌زمینه را انتخاب کنید:", reply_markup=simple_bg_kb(message.text))
        elif "متن استیکر هوش مصنوعی" in message.reply_to_message.text if message.reply_to_message else False:
            user_data = get_user(uid)
            if not is_admin and user_data.get("ai_used", 0) >= DAILY_LIMIT:
                await message.answer("سهمیه امروز تمام شد!")
                return
            await message.answer("موقعیت عمودی متن را انتخاب کنید:", reply_markup=ai_vpos_kb(message.text))
        else:
            await message.answer("لطفاً از منوی اصلی یکی از گزینه‌ها را انتخاب کنید:", reply_markup=main_menu_kb(is_admin))

__all__ = ['router']
