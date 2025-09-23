import asyncio
import os
import re
from io import BytesIO
from enum import Enum
from typing import Dict, Any, Optional, Tuple, List

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, BotCommand, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# ========================
# پیکربندی ساده
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در محیط تنظیم کنید.")

# ========================
# داده‌ها و NLU ساده
# ========================
DEFAULT_PALETTE = [
    ("سفید", "#FFFFFF"),
    ("مشکی", "#000000"),
    ("قرمز", "#F43F5E"),
    ("آبی", "#3B82F6"),
    ("سبز", "#22C55E"),
    ("زرد", "#EAB308"),
    ("بنفش", "#8B5CF6"),
    ("نارنجی", "#F97316"),
]
NAME_TO_HEX = {name: hx for name, hx in DEFAULT_PALETTE}

POS_WORDS = {"بالا": "top", "وسط": "center", "میانه": "center", "پایین": "bottom"}
SIZE_WORDS = {"ریز": "small", "کوچک": "small", "متوسط": "medium", "بزرگ": "large", "درشت": "large"}

def infer_from_text(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    t = (text or "").strip()
    for k, v in POS_WORDS.items():
        if k in t: out["position"] = v; break
    for k, v in SIZE_WORDS.items():
        if k in t: out["size"] = v; break
    for name, hx in NAME_TO_HEX.items():
        if name in t: out["color"] = hx; break
    m = re.search(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", t)
    if m: out["color"] = "#" + m.group(1)
    return out

# ========================
# ذخیره نشست ساده در حافظه
# ========================
_SESSIONS: Dict[int, Dict[str, Any]] = {}
_DEFAULT = {"text": None, "position": None, "font": None, "color": None, "size": None}

def get_session(uid: int) -> Dict[str, Any]:
    if uid not in _SESSIONS: _SESSIONS[uid] = _DEFAULT.copy()
    return _SESSIONS[uid]

def update_session(uid: int, data: Dict[str, Any]) -> None:
    s = get_session(uid); s.update({k: v for k, v in data.items() if v is not None})

def reset_session(uid: int) -> None:
    _SESSIONS[uid] = _DEFAULT.copy()

# ========================
# کشف فونت‌های سیستم (اختیاری)
# ========================
def find_arabic_fonts() -> Dict[str, str]:
    found: Dict[str, str] = {}
    candidates = [
        ("NotoNaskh", "NotoNaskhArabic"), ("NotoSansArabic", "NotoSansArabic"),
        ("Vazirmatn", "Vazirmatn"), ("Amiri", "Amiri"), ("Scheherazade", "Scheherazade"),
        ("IranSans", "IRANSans"), ("Sahel", "Sahel")
    ]
    roots = [
        "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
        "/usr/share/fonts/truetype", "/usr/share/fonts/opentype"
    ]
    for root in roots:
        if not os.path.isdir(root): continue
        for base, key in candidates:
            if base in found: continue
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    low = fn.lower()
                    if any(tag.lower() in low for tag in [key, base, base.replace(" ", "")]) and (low.endswith('.ttf') or low.endswith('.otf')):
                        path = os.path.join(dirpath, fn)
                        found[base] = path
                        break
    return found

_SYSTEM_FONTS = find_arabic_fonts()

def available_font_options() -> List[Tuple[str, str]]:
    keys = list(_SYSTEM_FONTS.keys())
    if not keys: return [("Default", "Default")]
    return [(k, k) for k in keys[:6]]

def resolve_font_path(font_key: Optional[str]) -> str:
    if font_key and font_key in _SYSTEM_FONTS: return _SYSTEM_FONTS[font_key]
    if _SYSTEM_FONTS:
        return next(iter(_SYSTEM_FONTS.values()))
    return ""

# ========================
# رندر استیکر
# ========================
CANVAS = (512, 512)

def _prepare_text(text: str) -> str:
    reshaped = arabic_reshaper.reshape(text or "")
    return get_display(reshaped)

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip('#')
    if len(hx) == 3:
        r, g, b = [int(c*2, 16) for c in hx]
    else:
        r = int(hx[0:2], 16); g = int(hx[2:4], 16); b = int(hx[4:6], 16)
    return (r, g, b, 255)

def wrap_text_to_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = text.split()
    if not words: return [text]
    lines: List[str] = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def fit_font_size(draw: ImageDraw.ImageDraw, text: str, font_path: str, base: int, max_w: int, max_h: int) -> int:
    size = base
    while size > 18:
        try:
            font = ImageFont.truetype(font_path, size=size) if font_path else ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        lines = wrap_text_to_width(draw, text, font, max_w)
        bbox = draw.multiline_textbbox((0,0), "\n".join(lines), font=font, spacing=6, align="center", stroke_width=2)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        if tw <= max_w and th <= max_h: return size
        size -= 2
    return max(size, 18)

def render_image(text: str, position: str, font_key: str, color_hex: str, size_key: str, as_webp: bool) -> bytes:
    W, H = CANVAS
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    color = _parse_hex(color_hex)
    padding = 28
    box_w, box_h = W - 2*padding, H - 2*padding
    size_map = {"small": 42, "medium": 64, "large": 92}
    base_size = size_map.get(size_key, 64)

    font_path = resolve_font_path(font_key)
    try:
        font = ImageFont.truetype(font_path, size=base_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    txt = _prepare_text(text)
    final_size = fit_font_size(draw, txt, font_path, base_size, box_w, box_h)
    try:
        font = ImageFont.truetype(font_path, size=final_size) if font_path else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    lines = wrap_text_to_width(draw, txt, font, box_w)
    wrapped = "\n".join(lines)

    bbox = draw.multiline_textbbox((0,0), wrapped, font=font, spacing=6, align="center", stroke_width=2)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]

    if position == "top": y = padding + th/2
    elif position == "bottom": y = H - padding - th/2
    else: y = H/2

    draw.multiline_text(
        (W/2, y),
        wrapped,
        font=font,
        fill=color,
        anchor="mm",
        align="center",
        spacing=6,
        stroke_width=2,
        stroke_fill=(0,0,0,220)
    )

    buf = BytesIO()
    if as_webp:
        img.save(buf, format="WEBP")
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()

# ========================
# جریان گفتگو
# ========================
class Step(Enum):
    TEXT = "text"
    POSITION = "position"
    FONT = "font"
    COLOR = "color"
    SIZE = "size"
    PREVIEW = "preview"

def missing_step(s: Dict[str, Any]) -> Optional[Step]:
    if not s["text"]: return Step.TEXT
    if not s["position"]: return Step.POSITION
    if not s["font"]: return Step.FONT
    if not s["color"]: return Step.COLOR
    if not s["size"]: return Step.SIZE
    return None

def step_question(uid: int, force_first_missing: bool = False) -> Dict[str, Any]:
    s = get_session(uid)
    m = missing_step(s)
    if not m and not force_first_missing:
        return {"step": Step.PREVIEW}

    if m == Step.TEXT or (force_first_missing and not s["text"]):
        return {"step": Step.TEXT, "question": "لطفاً متن استیکر را بفرست ✍️", "options": [], "prefix": "text"}

    if m == Step.POSITION or (force_first_missing and not s["position"]):
        opts = [("بالا ⬆️", "top"), ("وسط ⚪️", "center"), ("پایین ⬇️", "bottom")]
        return {"step": Step.POSITION, "question": "متن کجای استیکر قرار بگیرد؟", "options": opts, "prefix": "pos"}

    if m == Step.FONT or (force_first_missing and not s["font"]):
        fonts = available_font_options()
        return {"step": Step.FONT, "question": "چه فونتی دوست داری؟", "options": fonts, "prefix": "font"}

    if m == Step.COLOR or (force_first_missing and not s["color"]):
        opts = [(name, hx) for name, hx in DEFAULT_PALETTE]
        return {"step": Step.COLOR, "question": "رنگ متن را انتخاب کن:", "options": opts, "prefix": "color"}

    if m == Step.SIZE or (force_first_missing and not s["size"]):
        opts = [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]
        return {"step": Step.SIZE, "question": "اندازه متن؟", "options": opts, "prefix": "size"}

    return {"step": Step.PREVIEW}

def summarize(uid: int) -> str:
    s = get_session(uid)
    parts = []
    if s["text"]: parts.append(f"متن: {s['text']}")
    if s["position"]: parts.append({"top":"بالا","center":"وسط","bottom":"پایین"}[s["position"]])
    if s["font"]: parts.append(f"فونت: {s['font']}")
    if s["color"]: parts.append(f"رنگ: {s['color']}")
    if s["size"]: parts.append({"small":"کوچک","medium":"متوسط","large":"بزرگ"}[s["size"]])
    return " | ".join(parts) if parts else "تنظیمات هنوز کامل نیست."

# ========================
# Aiogram
# ========================
router = Router()

@router.message(F.text == "/start")
async def on_start(message: Message):
    reset_session(message.from_user.id)
    await message.answer("سلام! 👋\nبرای شروع متن استیکر را بفرست یا بنویس: می‌خوام استیکر بسازم")

@router.message(F.text.func(lambda t: t and "استیکر" in t))
async def on_make_sticker(message: Message):
    reset_session(message.from_user.id)
    await message.answer("عالی! متن استیکر را بفرست.")

@router.message()
async def on_message(message: Message):
    uid = message.from_user.id
    text = (message.text or "").strip()
    if not text:
        await message.answer("لطفاً متن بفرست تا شروع کنیم.")
        return

    s = get_session(uid)

    if not s["text"]:
        update_session(uid, {"text": text})

    inferred = infer_from_text(text)
    if inferred:
        update_session(uid, inferred)

    step = step_question(uid)
    if step["step"] == Step.PREVIEW:
        img_bytes = render_image(
            text=s.get("text") or "",
            position=s.get("position") or "center",
            font_key=s.get("font") or "Default",
            color_hex=s.get("color") or "#FFFFFF",
            size_key=s.get("size") or "medium",
            as_webp=False
        )
        file_obj = BufferedInputFile(img_bytes, filename="preview.png")
        kb = InlineKeyboardBuilder()
        kb.button(text="تایید ✅", callback_data="confirm")
        kb.button(text="ویرایش ✏️", callback_data="edit")
        kb.adjust(2)
        await message.answer_photo(file_obj, caption=summarize(uid), reply_markup=kb.as_markup())
        return

    builder = InlineKeyboardBuilder()
    for label, val in step["options"]:
        builder.button(text=label, callback_data=f"{step['prefix']}:{val}")
    builder.adjust(3)
    await message.answer(summarize(uid) + "\n\n" + step["question"], reply_markup=builder.as_markup())

@router.callback_query(F.data == "edit")
async def on_edit(cb: CallbackQuery):
    st = step_question(cb.from_user.id, force_first_missing=True)
    builder = InlineKeyboardBuilder()
    for label, val in st["options"]:
        builder.button(text=label, callback_data=f"{st['prefix']}:{val}")
    builder.adjust(3)
    await cb.message.answer(st["question"], reply_markup=builder.as_markup())
    await cb.answer()

@router.callback_query(F.data == "confirm")
async def on_confirm(cb: CallbackQuery):
    s = get_session(cb.from_user.id)
    img_bytes = render_image(
        text=s.get("text") or "",
        position=s.get("position") or "center",
        font_key=s.get("font") or "Default",
        color_hex=s.get("color") or "#FFFFFF",
        size_key=s.get("size") or "medium",
        as_webp=True
    )
    sticker_file = BufferedInputFile(img_bytes, filename="sticker.webp")
    await cb.message.answer_sticker(sticker=sticker_file)
    reset_session(cb.from_user.id)
    await cb.answer("استیکر ارسال شد! 🎉")

@router.callback_query(F.data.func(lambda d: d and any(d.startswith(p + ":") for p in ["pos","font","color","size"])))
async def on_option(cb: CallbackQuery):
    prefix, value = cb.data.split(":", 1)
    if prefix == "pos": update_session(cb.from_user.id, {"position": value})
    elif prefix == "font": update_session(cb.from_user.id, {"font": value})
    elif prefix == "color": update_session(cb.from_user.id, {"color": value})
    elif prefix == "size": update_session(cb.from_user.id, {"size": value})

    st = step_question(cb.from_user.id)
    if st["step"] == Step.PREVIEW:
        s = get_session(cb.from_user.id)
        img_bytes = render_image(
            text=s.get("text") or "",
            position=s.get("position") or "center",
            font_key=s.get("font") or "Default",
            color_hex=s.get("color") or "#FFFFFF",
            size_key=s.get("size") or "medium",
            as_webp=False
        )
        file_obj = BufferedInputFile(img_bytes, filename="preview.png")
        kb = InlineKeyboardBuilder()
        kb.button(text="تایید ✅", callback_data="confirm")
        kb.button(text="ویرایش ✏️", callback_data="edit")
        kb.adjust(2)
        await cb.message.answer_photo(file_obj, caption=summarize(cb.from_user.id), reply_markup=kb.as_markup())
        await cb.answer("پیش‌نمایش آماده شد.")
        return

    builder = InlineKeyboardBuilder()
    for label, val in st["options"]:
        builder.button(text=label, callback_data=f"{st['prefix']}:{val}")
    builder.adjust(3)
    await cb.message.answer(summarize(cb.from_user.id) + "\n\n" + st["question"], reply_markup=builder.as_markup())
    await cb.answer("ثبت شد ✅")

async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="شروع"),
    ])

async def main():
    # روش جدید تنظیم سبک پیام برای رفع هشدار
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await set_commands(bot)

    # خاموش کردن وبهوک فعال قبل از شروع تا تداخل نداشته باشیم
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print("deleteWebhook failed (ignored):", e)

    print("Bot is running. Press Ctrl+C to stop.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
