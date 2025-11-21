#!/usr/bin/env python3
"""
ربات تلگرامی استیکر ساز - نسخه نهایی با دکمه‌های شیشه‌ای
فقط برای سرورهای عادی (Railway/Render/Heroku) - نه Vercel!

Vercel نمی‌تواند این ربات را اجرا کند چون این ربات سرورLESS نیست.
برای Vercel به وب اپ نیاز دارید، اما ربات ما فقط bot عادی است.
"""

import asyncio
import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import subprocess
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
        }
    return SESSIONS[uid]

def reset_mode(uid: int):
    s = sess(uid)
    s["mode"] = "menu"
    s["ai"] = {}
    s["simple"] = {}
    s["pack_wizard"] = {}
    s["await_feedback"] = False
    s["last_sticker"] = None

# ============ توابع فونت ===============
def _load_local_fonts() -> Dict[str, str]:
    return {
        "vazir": "Vazirmatn-Regular.ttf",
        "sans": "DejaVuSans.ttf",
        "roboto": "Roboto-Regular.ttf"
    }

def available_font_options() -> List[Tuple[str, str]]:
    return [
        ("vazir", "فارسی زیبا"),
        ("sans", "ساده فانتزی"),
        ("roboto", "روبوتو")
    ]

def _detect_language(text: str) -> str:
    if re.search(r'[\u0600-\u06FF]', text):
        return "persian"
    elif re.search(r'[\u0750-\u077F]', text):
        return "arabic"
    return "latin"

def resolve_font_path(font_key: Optional[str], text: str = "") -> str:
    fonts = _load_local_fonts()
    
    if font_key and font_key in fonts:
        return fonts[font_key]
    
    lang = _detect_language(text) if text else "persian"
    if lang == "persian":
        return fonts["vazir"]
    return fonts["sans"]

def _prepare_text(text: str) -> str:
    text = text.strip()
    if len(text) > 150:
        words = text.split()
        text = ' '.join(words[:30])
        if len(text) < len(text.strip()):
            text += "..."
    return text

def is_persian(text):
    return bool(re.search(r'[\u0600-\u06FF]', text))

def is_ffmpeg_installed() -> bool:
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
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

async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = hx.lstrip('#')
    if len(hx) == 3:
        hx = ''.join(c*2 for c in hx)
    try:
        rgb = tuple(int(hx[i:i+2], 16) for i in (0, 2, 4))
        return (*rgb, 255)
    except:
        return (0, 0, 0, 255)

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    for size in range(base, 20, -1):
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= max_w and h <= max_h:
            return size
    return 25

def _make_default_bg(size=(512, 512)) -> Image.Image:
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    for i in range(0, size[0], 40):
        for j in range(0, size[1], 40):
            if (i // 40 + j // 40) % 2 == 0:
                draw.rectangle([(i, j), (i+39, j+39)], fill=(255, 255, 255, 20))
    
    return img

def render_image(text: str, v_pos: str, h_pos: str, font_key: str, color_hex: str, size_key: str,
                 bg_mode: str = "default") -> Image.Image:
    W, H = 512, 512
    text = _prepare_text(text)
    
    if is_persian(text):
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            text = get_display(reshaped_text)
        except:
            pass
    
    img = _make_default_bg((W, H)) if bg_mode == "default" else Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font_path = resolve_font_path(font_key, text)
        base_size = 70 if size_key == "large" else 55 if size_key == "medium" else 40
        final_size = fit_font_size(draw, text, font_path, base_size, W-60, H-60)
        font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    if h_pos == "left":
        x = 20
    elif h_pos == "right":
        x = W - text_w - 20
    else:
        x = (W - text_w) // 2
    
    if v_pos == "top":
        y = 20
    elif v_pos == "bottom":
        y = H - text_h - 20
    else:
        y = (H - text_h) // 2
    
    color = _parse_hex(color_hex)
    draw.text((x, y), text, fill=color, font=font)
    return img

# ============ منوی اصلی با دکمه‌های شیشه‌ای ============
def main_menu_kb(is_admin: bool = False):
    builder = InlineKeyboardBuilder()
    
    # ردیف اول - دکمه‌های اصلی شیشه‌ای
    builder.row(
        InlineKeyboardButton(text="🎨 ساخت استیکر سریع", callback_data="simple_mode"),
        InlineKeyboardButton(text="✨ استیکر پیشرفته", callback_data="ai_mode")
    )
    
    # ردیف دوم - مدیریت
    builder.row(
        InlineKeyboardButton(text="📦 مدیریت پک‌ها", callback_data="pack_manage"),
        InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="settings")
    )
    
    # ردیف سوم - اطلاعاتی
    builder.row(
        InlineKeyboardButton(text="📊 آمار کاربری", callback_data="user_stats"),
        InlineKeyboardButton(text="❓ راهنما", callback_data="help_menu")
    )
    
    # ردیف چهارم - لینک‌ها
    builder.row(
        InlineKeyboardButton(text="🌐 کانال", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"),
        InlineKeyboardButton(text="💬 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")
    )
    
    if is_admin:
        builder.row(InlineKeyboardButton(text="🔧 پنل ادمین", callback_data="admin_panel"))
    
    return builder.as_markup()

# ============ ربات ===============
router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    uid = message.from_user.id
    reset_mode(uid)
    
    welcome_text = f"""
✨ **به ربات استیکر ساز خوش آمدید!** ✨

🎯 یک ربات حرفه‌ای برای ساخت استیکرهای شخصی با کیفیت بالا

🔥 **ویژگی‌های اصلی:**
• 🎨 ساخت استیکر متن (فارسی و انگلیسی)
• 🎬 تبدیل ویدیو به استیکر متحرک
• 📦 مدیریت پک‌های استیکر
• 🌟 کیفیت عالی و سرعت بالا

📝 **لطفاً یکی از گزینه‌های زیر را انتخاب کنید:**
    """
    
    is_admin = (uid == ADMIN_ID)
    await message.answer(welcome_text, reply_markup=main_menu_kb(is_admin))

@router.callback_query(F.data == "simple_mode")
async def simple_mode_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    sess(uid)["mode"] = "simple"
    
    text = """
🎨 **ساخت استیکر سریع**

لطفاً متن مورد نظر خود را بنویسید یا عکس/ویدیو بفرستید:

⚡ نکات:
• متن: حداکثر 150 کاراکتر
• عکس: تبدیل به استیکر با متن
• ویدیو: تبدیل به استیکر متحرک
• پشتیبانی از فارسی و انگلیسی
    """
    
    await callback.message.edit_text(text, reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    await callback.answer()

def back_to_menu_kb(is_admin: bool = False):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="back_to_menu"))
    if is_admin:
        builder.row(InlineKeyboardButton(text="🔧 پنل ادمین", callback_data="admin_panel"))
    return builder.as_markup()

@router.callback_query(F.data == "ai_mode")
async def ai_mode_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    u = user(uid)
    left = _quota_left(u, uid == ADMIN_ID)
    
    if left <= 0 and uid != ADMIN_ID:
        await callback.message.edit_text(
            "❌ سهمیه شما امروز تمام شده است!\n\n"
            "برای استفاده بیشتر به کانال ما بپیوندید:\n"
            f"📺 {CHANNEL_USERNAME}",
            reply_markup=back_to_menu_kb(False)
        )
        await callback.answer()
        return
    
    sess(uid)["mode"] = "ai"
    sess(uid)["ai"] = {}
    
    text = f"""
✨ **استیکر پیشرفته**

🎯 سهمیه باقی‌مانده: {left} استیکر

لطفاً نوع استیکر را انتخاب کنید:
    """
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 متن پیشرفته", callback_data="ai:text"),
        InlineKeyboardButton(text="🎬 ویدیو به استیکر", callback_data="ai:video")
    )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_menu"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: CallbackQuery):
    uid = callback.from_user.id
    reset_mode(uid)
    
    text = """
🏠 **منوی اصلی**

لطفاً خدمات مورد نظر را انتخاب کنید:
    """
    
    is_admin = (uid == ADMIN_ID)
    await callback.message.edit_text(text, reply_markup=main_menu_kb(is_admin))
    await callback.answer()

@router.callback_query(F.data.startswith("ai:"))
async def ai_mode_callback(callback: CallbackQuery):
    uid = callback.from_user.id
    action = callback.data.split(":")[1]
    s = sess(uid)
    
    if action == "text":
        s["ai"]["sticker_type"] = "image"
        await callback.message.edit_text(
            "✨ **متن پیشرفته**\n\n"
            "لطفاً متن خود را بنویسید (تا 150 کاراکتر):",
            reply_markup=back_to_menu_kb(uid == ADMIN_ID)
        )
    elif action == "video":
        s["ai"]["sticker_type"] = "video"
        await callback.message.edit_text(
            "🎬 **ویدیو به استیکر**\n\n"
            "لطفاً ویدیوی خود را بفرستید:\n"
            "• حداکثر حجم: 50MB\n"
            "• فرمت‌های: MP4, AVI, MOV",
            reply_markup=back_to_menu_kb(uid == ADMIN_ID)
        )
    
    await callback.answer()

@router.message()
async def message_handler(message: Message):
    uid = message.from_user.id
    is_admin = (uid == ADMIN_ID)
    s = sess(uid)
    
    if MAINTENANCE and not is_admin:
        await message.answer("🔧 ربات در حال تعمیر است. لطفاً بعداً تلاش کنید.")
        return
    
    if message.photo and s.get("mode") == "simple":
        await message.answer("📷 عکس دریافت شد. لطفاً متن استیکر را بفرستید:")
        return
    
    if message.video and s.get("mode") == "ai" and s["ai"].get("sticker_type") == "video":
        await message.answer("🎬 در حال پردازش ویدیو...")
        file = await message.bot.download(message.video.file_id)
        webm_bytes = await process_video_to_webm(file.read())
        
        if webm_bytes:
            sess(uid)["last_sticker"] = webm_bytes
            await message.answer_sticker(BufferedInputFile(webm_bytes, "sticker.webm"))
            await message.answer("✅ استیکر ویدیویی شما با موفقیت ساخته شد!", reply_markup=back_to_menu_kb(is_admin))
            
            u = user(uid)
            if not is_admin:
                u["ai_used"] += 1
        else:
            await message.answer("❌ پردازش ویدیو با خطا مواجه شد.", reply_markup=back_to_menu_kb(is_admin))
        return
    
    mode = s.get("mode", "menu")
    
    if mode == "simple":
        if message.text:
            s["simple"]["text"] = message.text.strip()
            await message.answer("🎨 در حال ساخت استیکر شما...")
            
            try:
                img = render_image(
                    text=message.text,
                    v_pos="center",
                    h_pos="center", 
                    font_key="vazir",
                    color_hex="#FFFFFF",
                    size_key="large",
                    bg_mode="default"
                )
                
                bio = BytesIO()
                bio.name = 'sticker.png'
                img.save(bio, 'PNG')
                bio.seek(0)
                
                await message.answer_sticker(BufferedInputFile(bio.read(), 'sticker.webp'))
                await message.answer("✅ استیکر شما با موفقیت ساخته شد!", reply_markup=back_to_menu_kb(is_admin))
                
            except Exception as e:
                await message.answer(f"❌ خطا در ساخت استیکر: {str(e)}", reply_markup=back_to_menu_kb(is_admin))
    
    elif mode == "ai":
        if message.text and s["ai"].get("sticker_type") == "image":
            u = user(uid)
            left = _quota_left(u, is_admin)
            if left <= 0 and not is_admin:
                await message.answer("❌ سهمیه شما تمام شد!", reply_markup=back_to_menu_kb(is_admin))
                return
            
            s["ai"]["text"] = message.text.strip()
            await message.answer("🎨 در حال ساخت استیکر پیشرفته...")
            
            try:
                img = render_image(
                    text=message.text,
                    v_pos="center",
                    h_pos="center", 
                    font_key="vazir",
                    color_hex="#FF6B6B",
                    size_key="large",
                    bg_mode="transparent"
                )
                
                bio = BytesIO()
                bio.name = 'sticker.png'
                img.save(bio, 'PNG')
                bio.seek(0)
                
                await message.answer_sticker(BufferedInputFile(bio.read(), 'sticker.webp'))
                await message.answer("✅ استیکر پیشرفته شما با موفقیت ساخته شد!", reply_markup=back_to_menu_kb(is_admin))
                
                if not is_admin:
                    u["ai_used"] += 1
                
            except Exception as e:
                await message.answer(f"❌ خطا در ساخت استیکر: {str(e)}", reply_markup=back_to_menu_kb(is_admin))
    
    else:
        is_admin = (uid == ADMIN_ID)
        await message.answer("🏠 از منوی اصلی انتخاب کنید:", reply_markup=main_menu_kb(is_admin))

async def main():
    global BOT_USERNAME

    dp = Dispatcher()
    dp.include_router(router)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    bot_info = await bot.get_me()
    BOT_USERNAME = bot_info.username
    print(f"ربات با نام کاربری @{BOT_USERNAME} شروع به کار کرد")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())