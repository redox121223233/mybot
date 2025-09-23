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
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# ========================
# پیکربندی
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در محیط تنظیم کنید.")

CHANNEL_USERNAME = "@redoxbot_sticker"  # عضویت اجباری
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919

# حالت نگهداری برای بخش هوش مصنوعی
MAINTENANCE = False

# ========================
# ذخیره کاربران/نشست‌ها/آمار (در حافظه)
# ========================
USERS: Dict[int, Dict[str, Any]] = {}  # {user_id: {ai_used:int, vote:str|None}}
SESSIONS: Dict[int, Dict[str, Any]] = {}  # {user_id: {...}}
ADMIN_PENDING: Dict[int, Dict[str, Any]] = {}  # برای درخواست‌های پاسخ‌دار ادمین

def user(uid: int) -> Dict[str, Any]:
    if uid not in USERS:
        USERS[uid] = {"ai_used": 0, "vote": None}
    return USERS[uid]

def sess(uid: int) -> Dict[str, Any]:
    if uid not in SESSIONS:
        SESSIONS[uid] = {"mode": "menu", "ai": {}, "simple": {}}
    return SESSIONS[uid]

def reset_mode(uid: int):
    s = sess(uid)
    s["mode"] = "menu"
    s["ai"] = {}
    s["simple"] = {}

# ========================
# NLU ساده و داده‌های UI
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
# فونت
# ========================
def find_arabic_fonts() -> Dict[str, str]:
    found: Dict[str, str] = {}
    candidates = [
        ("NotoNaskh", "NotoNaskhArabic"), ("NotoSansArabic", "NotoSansArabic"),
        ("Vazirmatn", "Vazirmatn"), ("Amiri", "Amiri"), ("Scheherazade", "Scheherazade"),
        ("Sahel", "Sahel"), ("IRANSans", "IRANSans")
    ]
    roots = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"), "/usr/share/fonts/truetype", "/usr/share/fonts/opentype"]
    for root in roots:
        if not os.path.isdir(root): continue
        for base, key in candidates:
            if base in found: continue
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    low = fn.lower()
                    if any(tag.lower() in low for tag in [key, base, base.replace(" ", "")]) and (low.endswith(".ttf") or low.endswith(".otf")):
                        found[base] = os.path.join(dirpath, fn); break
    return found

_SYSTEM_FONTS = find_arabic_fonts()

def available_font_options() -> List[Tuple[str, str]]:
    keys = list(_SYSTEM_FONTS.keys())
    return [(k, k) for k in keys[:8]] if keys else [("Default", "Default")]

def resolve_font_path(font_key: Optional[str]) -> str:
    if font_key and font_key in _SYSTEM_FONTS: return _SYSTEM_FONTS[font_key]
    return next(iter(_SYSTEM_FONTS.values()), "")

# ========================
# رندر تصویر/استیکر
# ========================
CANVAS = (512, 512)

def _prepare_text(text: str) -> str:
    reshaped = arabic_reshaper.reshape(text or "")
    return get_display(reshaped)

def _parse_hex(hx: str) -> Tuple[int,int,int,int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
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

def _make_default_bg(size=(512,512)) -> Image.Image:
    # گرادیان ملایم
    w, h = size
    img = Image.new("RGBA", size, (20,20,35,255))
    top = (56, 189, 248)  # فیروزه‌ای
    bottom = (99, 102, 241)  # ایندیگو
    for y in range(h):
        t = y / (h-1)
        r = int(top[0]*(1-t) + bottom[0]*t)
        g = int(top[1]*(1-t) + bottom[1]*t)
        b = int(top[2]*(1-t) + bottom[2]*t)
        ImageDraw.Draw(img).line([(0,y),(w,y)], fill=(r,g,b,255))
    return img.filter(ImageFilter.GaussianBlur(0.5))

def _compose_bg_photo(photo_bytes: bytes, size=(512,512)) -> Image.Image:
    base = Image.open(BytesIO(photo_bytes)).convert("RGBA")
    # crop center to cover 512x512
    bw, bh = base.size
    scale = max(size[0]/bw, size[1]/bh)
    nw, nh = int(bw*scale), int(bh*scale)
    base = base.resize((nw, nh), Image.LANCZOS)
    x = (nw - size[0]) // 2
    y = (nh - size[1]) // 2
    base = base.crop((x, y, x+size[0], y+size[1]))
    return base

def render_image(text: str, position: str, font_key: str, color_hex: str, size_key: str, bg_mode: str = "transparent", bg_photo: Optional[bytes] = None, as_webp: bool = False) -> bytes:
    W, H = CANVAS
    # پس‌زمینه
    if bg_mode == "default":
        img = _make_default_bg((W,H))
    elif bg_mode == "photo" and bg_photo:
        img = _compose_bg_photo(bg_photo, (W,H))
    else:
        img = Image.new("RGBA", (W,H), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    color = _parse_hex(color_hex)
    padding = 28
    box_w, box_h = W - 2*padding, H - 2*padding

    # اندازه‌های بزرگ‌تر مخصوص فارسی
    size_map = {"small": 52, "medium": 80, "large": 112}
    base_size = size_map.get(size_key, 80)

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

    # سایه/خط دور برای خوانایی
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
    img.save(buf, format="WEBP" if as_webp else "PNG")
    return buf.getvalue()

# ========================
# ابزار UI
# ========================
def main_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر ساده 🪄", callback_data="menu:simple")
    kb.button(text="استیکر هوش مصنوعی 🤖", callback_data="menu:ai")
    kb.button(text="اشتراک / نظرسنجی 📊", callback_data="menu:sub")
    kb.button(text="پشتیبانی 🛟", callback_data="menu:support")
    if is_admin:
        kb.button(text="پنل ادمین 🛠", callback_data="menu:admin")
    kb.adjust(2,2,1)
    return kb.as_markup()

def join_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="عضویت در کانال 🔗", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
    kb.button(text="عضو شدم ✅", callback_data="check_sub")
    kb.adjust(1,1)
    return kb.as_markup()

def back_to_menu_kb(is_admin: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="بازگشت به منو ⬅️", callback_data="menu:home")
    if is_admin:
        kb.button(text="پنل ادمین 🛠", callback_data="menu:admin")
    kb.adjust(1,1)
    return kb.as_markup()

# ========================
# عضویت اجباری
# ========================
async def is_member(bot: Bot, uid: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=uid)
        status = getattr(member, "status", None)
        return str(status) in ("ChatMemberStatus.MEMBER","member","administrator","creator","ChatMemberStatus.ADMINISTRATOR","ChatMemberStatus.CREATOR")
    except TelegramBadRequest:
        # اگر کانال خصوصی باشد و بات دسترسی نداشته باشد، برای جلوگیری از گیر کردن، اجازه می‌دهیم
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

# ========================
# ربات و روتر
# ========================
router = Router()

@router.message(CommandStart())
async def on_start(message: Message):
    reset_mode(message.from_user.id)
    if not await ensure_membership(message): return
    await message.answer("سلام! خوش اومدی ✨")
یکی از گزینه‌های زیر رو انتخاب کن:", reply_markup=main_menu_kb(is_admin=(message.from_user.id==ADMIN_ID)))

@router.callback_query(F.data == "check_sub")
async def on_check_sub(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    await cb.message.answer("عالی! حالا از منو یکی را انتخاب کن:", reply_markup=main_menu_kb(is_admin=(cb.from_user.id==ADMIN_ID)))
    await cb.answer("عضویت تایید شد ✅")

# ========== منوها ==========
@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    reset_mode(cb.from_user.id)
    await cb.message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin=(cb.from_user.id==ADMIN_ID)))
    await cb.answer()

@router.callback_query(F.data == "menu:support")
async def on_support(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    await cb.message.answer(f"پشتیبانی: {SUPPORT_USERNAME}", reply_markup=back_to_menu_kb(cb.from_user.id==ADMIN_ID))
    await cb.answer("باز شد")

@router.callback_query(F.data == "menu:sub")
async def on_sub(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    u = user(cb.from_user.id)
    yes = sum(1 for v in USERS.values() if v.get("vote")=="yes")
    no = sum(1 for v in USERS.values() if v.get("vote")=="no")
    kb = InlineKeyboardBuilder()
    kb.button(text="بله ✅", callback_data="vote:yes")
    kb.button(text="خیر ❌", callback_data="vote:no")
    kb.button(text="بازگشت ⬅️", callback_data="menu:home")
    kb.adjust(2,1)
    await cb.message.answer(f"اشتراک بیاریم؟
رأی شما: {('بله' if u.get('vote')=='yes' else ('خیر' if u.get('vote')=='no' else 'ثبت نشده'))}
آمار فعلی: بله {yes} | خیر {no}", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("vote:")))
async def on_vote(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    choice = cb.data.split(":",1)[1]
    if choice in ("yes","no"):
        user(cb.from_user.id)["vote"] = choice
        await cb.answer("رأی ثبت شد ✅")
    else:
        await cb.answer("نامعتبر")
    # آپدیت صفحه
    yes = sum(1 for v in USERS.values() if v.get("vote")=="yes")
    no = sum(1 for v in USERS.values() if v.get("vote")=="no")
    await cb.message.edit_text(f"اشتراک بیاریم؟
رأی شما: {('بله' if choice=='yes' else 'خیر')}
آمار فعلی: بله {yes} | خیر {no}", reply_markup=back_to_menu_kb(cb.from_user.id==ADMIN_ID))

# ========== استیکر ساده ==========
@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    s = sess(cb.from_user.id)
    s["mode"] = "simple"
    s["simple"] = {"state":"ASK_TEXT", "text":None, "bg_mode":None, "bg_photo":None}
    await cb.message.answer("متن استیکر ساده رو بفرست ✍️", reply_markup=back_to_menu_kb(cb.from_user.id==ADMIN_ID))
    await cb.answer()

# ========== استیکر هوش مصنوعی ==========
@router.callback_query(F.data == "menu:ai")
async def on_ai(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    if MAINTENANCE:
        await cb.message.answer("بخش هوش مصنوعی موقتاً در دست تعمیر است 🛠", reply_markup=back_to_menu_kb(cb.from_user.id==ADMIN_ID))
        await cb.answer(); return
    u = user(cb.from_user.id)
    if u["ai_used"] >= 5:
        await cb.message.answer("حداکثر ۵ بار رایگان استفاده کرده‌ای.
اگر دوست داری اشتراک اضافه کنیم، در نظرسنجی رأی بده 📊", reply_markup=back_to_menu_kb(cb.from_user.id==ADMIN_ID))
        await cb.answer(); return
    s = sess(cb.from_user.id)
    s["mode"] = "ai"
    s["ai"] = {"text":None,"position":None,"font":None,"color":"#FFFFFF","size":None,"bg":"transparent","bg_photo":None}
    await cb.message.answer("متن استیکر رو بفرست ✍️", reply_markup=back_to_menu_kb(cb.from_user.id==ADMIN_ID))
    await cb.answer()

# ========== پنل ادمین ==========
def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="آمار 📈", callback_data="admin:stats")
    kb.button(text="رأی‌ها 📊", callback_data="admin:votes")
    kb.button(text="ریست سهمیه کاربر 🔄", callback_data="admin:reset_one")
    kb.button(text="ریست همه سهمیه‌ها 🧹", callback_data="admin:reset_all")
    kb.button(text="ارسال پیام به کاربر ✉️", callback_data="admin:pm")
    kb.button(text=f"{'خاموش' if MAINTENANCE else 'روشن'} کردن نگهداری 🛠", callback_data="admin:toggle_maint")
    kb.adjust(2,2,2)
    return kb.as_markup()

@router.callback_query(F.data == "menu:admin")
async def on_admin(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("اجازه دسترسی ندارید", show_alert=True); return
    await cb.message.answer("پنل ادمین:", reply_markup=admin_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:stats")
async def admin_stats(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return await cb.answer("No", show_alert=True)
    total_users = len(USERS)
    used = sum(1 for v in USERS.values() if v.get("ai_used",0)>0)
    votes_yes = sum(1 for v in USERS.values() if v.get("vote")=="yes")
    votes_no = sum(1 for v in USERS.values() if v.get("vote")=="no")
    await cb.message.answer(f"کاربران: {total_users}
کاربرانی که AI استفاده کردند: {used}
رأی‌ها: بله {votes_yes} | خیر {votes_no}")
    await cb.answer()

@router.callback_query(F.data == "admin:votes")
async def admin_votes(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return await cb.answer("No", show_alert=True)
    yes = [uid for uid,v in USERS.items() if v.get("vote")=="yes"]
    no = [uid for uid,v in USERS.items() if v.get("vote")=="no"]
    txt = f"بله: {len(yes)}
{yes[:20]}

خیر: {len(no)}
{no[:20]}"
    await cb.message.answer(txt)
    await cb.answer()

@router.callback_query(F.data == "admin:reset_one")
async def admin_reset_one(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return await cb.answer("No", show_alert=True)
    ADMIN_PENDING[ADMIN_ID] = {"action":"reset_quota"}
    await cb.message.answer("ID کاربر را بفرست تا سهمیه AI او ریست شود.")
    await cb.answer()

@router.callback_query(F.data == "admin:reset_all")
async def admin_reset_all(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return await cb.answer("No", show_alert=True)
    for v in USERS.values(): v["ai_used"] = 0
    await cb.message.answer("همه سهمیه‌ها ریست شد ✅")
    await cb.answer()

@router.callback_query(F.data == "admin:pm")
async def admin_pm(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return await cb.answer("No", show_alert=True)
    ADMIN_PENDING[ADMIN_ID] = {"action":"pm_user", "stage":"ask_id"}
    await cb.message.answer("ID کاربر را بفرست:")
    await cb.answer()

@router.callback_query(F.data == "admin:toggle_maint")
async def admin_toggle_maint(cb: CallbackQuery):
    global MAINTENANCE
    if cb.from_user.id != ADMIN_ID: return await cb.answer("No", show_alert=True)
    MAINTENANCE = not MAINTENANCE
    await cb.message.answer(f"حالت نگهداری: {'فعال' if MAINTENANCE else 'غیرفعال'}")
    await cb.answer()

# ========== مدیریت پیام‌ها ==========
@router.message()
async def on_message(message: Message):
    uid = message.from_user.id
    # اول بررسی عضویت
    if not await ensure_membership(message): return

    # پردازش درخواست‌های معلق ادمین
    if uid == ADMIN_ID and ADMIN_PENDING.get(ADMIN_ID):
        p = ADMIN_PENDING[ADMIN_ID]
        if p["action"] == "reset_quota":
            try:
                target = int((message.text or "").strip())
                if target in USERS:
                    USERS[target]["ai_used"] = 0
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
                    await message.bot.send_message(chat_id=target, text=f"[پیام ادمین]
{message.text}")
                    await message.answer("ارسال شد ✅")
                except Exception as e:
                    await message.answer(f"ارسال نشد: {e}")
                ADMIN_PENDING.pop(ADMIN_ID, None)
                return

    s = sess(uid)
    mode = s.get("mode","menu")

    # استیکر ساده
    if mode == "simple":
        st = s["simple"]
        if st["state"] == "ASK_TEXT" and message.text:
            st["text"] = message.text.strip()
            st["state"] = "ASK_BG"
            kb = InlineKeyboardBuilder()
            kb.button(text="شفاف ♻️", callback_data="simple:bg:transparent")
            kb.button(text="ارسال عکس 🖼", callback_data="simple:bg:want_photo")
            kb.adjust(2)
            await message.answer("پس‌زمینه چطور باشه؟", reply_markup=kb.as_markup())
            return
        elif st["state"] == "WAIT_BG_PHOTO" and message.photo:
            largest = message.photo[-1]
            buf = BytesIO()
            await message.bot.download(largest, destination=buf)
            st["bg_mode"] = "photo"
            st["bg_photo"] = buf.getvalue()
            # ساخت خروجی
            img = render_image(text=st["text"], position="center", font_key="Default", color_hex="#FFFFFF", size_key="medium", bg_mode=st["bg_mode"], bg_photo=st["bg_photo"], as_webp=False)
            file_obj = BufferedInputFile(img, filename="preview.png")
            kb = InlineKeyboardBuilder()
            kb.button(text="تایید ✅", callback_data="simple:confirm")
            kb.button(text="بازگشت ⬅️", callback_data="menu:home")
            kb.adjust(2)
            await message.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=kb.as_markup())
            return
        else:
            await message.answer("لطفاً متن یا عکس موردنظر را بفرست.")
            return

    # استیکر هوش مصنوعی
    if mode == "ai":
        a = s["ai"]
        if a["text"] is None and message.text:
            a["text"] = message.text.strip()
            # پیشنهاد خودکار از NLU
            inferred = infer_from_text(a["text"])
            a.update(inferred)
            # سوال موقعیت
            kb = InlineKeyboardBuilder()
            for label, val in [("بالا ⬆️","top"),("وسط ⚪️","center"),("پایین ⬇️","bottom")]:
                kb.button(text=label, callback_data=f"ai:pos:{val}")
            kb.adjust(3)
            await message.answer("متن کجا قرار بگیرد؟", reply_markup=kb.as_markup()); return
        # اگر منتظر عکس بک‌گراند
        if a.get("bg") == "photo" and a.get("bg_photo") is None and message.photo:
            largest = message.photo[-1]
            buf = BytesIO()
            await message.bot.download(largest, destination=buf)
            a["bg_photo"] = buf.getvalue()
            # همه اسلات‌ها پر است؟ پیش‌نمایش
            if all(a.get(k) for k in ["text","position","font","color","size"]):
                await send_ai_preview(message, uid)
            else:
                await message.answer("ادامه تنظیمات را با دکمه‌ها انتخاب کن.")
            return

    # حالت پیش‌فرض
    await message.answer("از منو یکی را انتخاب کن:", reply_markup=main_menu_kb(is_admin=(uid==ADMIN_ID)))

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
    kb = InlineKeyboardBuilder()
    kb.button(text="تایید ✅", callback_data="ai:confirm")
    kb.button(text="ویرایش ✏️", callback_data="ai:edit")
    kb.button(text="بازگشت ⬅️", callback_data="menu:home")
    kb.adjust(2,1)
    if isinstance(message_or_cb, Message):
        await message_or_cb.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=kb.as_markup())
    else:
        await message_or_cb.message.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=kb.as_markup())

# ========== کال‌بک‌های ساده ==========
@router.callback_query(F.data.func(lambda d: d and d.startswith("simple:bg:")))
async def on_simple_bg(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    st = sess(cb.from_user.id)["simple"]
    act = cb.data.split(":")[-1]
    if act == "transparent":
        st["bg_mode"] = "transparent"
        img = render_image(text=st["text"], position="center", font_key="Default", color_hex="#FFFFFF", size_key="medium", bg_mode="transparent", as_webp=False)
        file_obj = BufferedInputFile(img, filename="preview.png")
        kb = InlineKeyboardBuilder()
        kb.button(text="تایید ✅", callback_data="simple:confirm")
        kb.button(text="بازگشت ⬅️", callback_data="menu:home")
        kb.adjust(2)
        await cb.message.answer_photo(file_obj, caption="پیش‌نمایش آماده است", reply_markup=kb.as_markup())
    elif act == "want_photo":
        st["state"] = "WAIT_BG_PHOTO"
        await cb.message.answer("عکس پس‌زمینه را ارسال کن 🖼")
    await cb.answer()

@router.callback_query(F.data == "simple:confirm")
async def on_simple_confirm(cb: CallbackQuery):
    st = sess(cb.from_user.id)["simple"]
    img = render_image(text=st["text"], position="center", font_key="Default", color_hex="#FFFFFF", size_key="medium", bg_mode=st.get("bg_mode") or "transparent", bg_photo=st.get("bg_photo"), as_webp=True)
    await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
    reset_mode(cb.from_user.id)
    await cb.answer("استیکر ارسال شد ✅")

# ========== کال‌بک‌های AI ==========
@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:")))
async def on_ai_callbacks(cb: CallbackQuery):
    if not await ensure_membership(cb): return
    if MAINTENANCE:
        await cb.answer("در دست تعمیر 🛠", show_alert=True); return
    u = user(cb.from_user.id)
    if u["ai_used"] >= 5 and not cb.data.startswith("ai:edit"):
        await cb.answer("سهمیه رایگان تمام شد", show_alert=True); return

    a = sess(cb.from_user.id)["ai"]
    _, action, value = (cb.data.split(":",2)+["",""])[:3]

    if action == "pos":
        a["position"] = value
        # فونت‌ها
        kb = InlineKeyboardBuilder()
        for label, val in available_font_options():
            kb.button(text=label, callback_data=f"ai:font:{val}")
        kb.adjust(3)
        await cb.message.answer("فونت را انتخاب کن:", reply_markup=kb.as_markup())
        return await cb.answer("ثبت شد")

    if action == "font":
        a["font"] = value
        # رنگ
        kb = InlineKeyboardBuilder()
        for name, hx in DEFAULT_PALETTE:
            kb.button(text=name, callback_data=f"ai:color:{hx}")
        kb.adjust(3)
        await cb.message.answer("رنگ متن:", reply_markup=kb.as_markup())
        return await cb.answer("ثبت شد")

    if action == "color":
        a["color"] = value
        # اندازه
        kb = InlineKeyboardBuilder()
        for label, val in [("کوچک","small"),("متوسط","medium"),("بزرگ","large")]:
            kb.button(text=label, callback_data=f"ai:size:{val}")
        kb.adjust(3)
        await cb.message.answer("اندازه متن:", reply_markup=kb.as_markup())
        return await cb.answer("ثبت شد")

    if action == "size":
        a["size"] = value
        # پس‌زمینه
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
        # غیرعکس → پیش‌نمایش
        if all(a.get(k) for k in ["text","position","font","color","size"]):
            await send_ai_preview(cb, cb.from_user.id)
            return await cb.answer("پیش‌نمایش آماده شد")

    if action == "edit":
        # شروع از اولین اسلات ناقص
        for step in ["position","font","color","size","bg"]:
            if not a.get(step) or (step=="bg" and a["bg"]=="photo" and not a.get("bg_photo")):
                if step == "position":
                    kb = InlineKeyboardBuilder()
                    for label, val in [("بالا ⬆️","top"),("وسط ⚪️","center"),("پایین ⬇️","bottom")]:
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
                    for label, val in [("کوچک","small"),("متوسط","medium"),("بزرگ","large")]:
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
        # تولید استیکر و افزایش سهمیه
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
        await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
        user(cb.from_user.id)["ai_used"] += 1
        reset_mode(cb.from_user.id)
        return await cb.answer("استیکر ارسال شد ✅")

# ========================
# دستورات پایه
# ========================
async def set_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="شروع"),
    ])

async def main():
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
