# --- handlers.py ---
import os
import re
import asyncio
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display
from aiogram import F, Router, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

# =============== پیکربندی ===============
CHANNEL_USERNAME = "@redoxbot_sticker"
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919
DAILY_LIMIT = 5
BOT_USERNAME = ""

# ============ فیلتر کلمات نامناسب ============
FORBIDDEN_WORDS = ["kos", "kir", "kon", "koss", "kiri", "koon"]

# ============ حافظه ساده (in-memory) ============
USERS: Dict[int, Dict[str, Any]] = {}
SESSIONS: Dict[int, Dict[str, Any]] = {}

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
            "ai_used": 0, "vote": None, "day_start": _today_start_ts(),
            "packs": [], "current_pack": None
        }
    _reset_daily_if_needed(USERS[uid])
    return USERS[uid]

def sess(uid: int) -> Dict[str, Any]:
    if uid not in SESSIONS:
        SESSIONS[uid] = {
            "mode": "menu", "ai": {}, "simple": {}, "pack_wizard": {},
            "await_feedback": False, "last_sticker": None, "admin": {}
        }
    return SESSIONS[uid]

# ============ توابع مدیریت پک‌های کاربر ============
def get_user_packs(uid: int) -> List[Dict[str, str]]:
    return user(uid).get("packs", [])

def add_user_pack(uid: int, pack_name: str, pack_short_name: str):
    u = user(uid)
    packs = u.get("packs", [])
    if any(p["short_name"] == pack_short_name for p in packs):
        return
    packs.append({"name": pack_name, "short_name": pack_short_name})
    u["packs"] = packs
    u["current_pack"] = pack_short_name

def set_current_pack(uid: int, pack_short_name: str):
    user(uid)["current_pack"] = pack_short_name

def get_current_pack(uid: int) -> Optional[Dict[str, str]]:
    u = user(uid)
    current_pack_short_name = u.get("current_pack")
    if current_pack_short_name:
        for pack in u.get("packs", []):
            if pack["short_name"] == current_pack_short_name:
                return pack
    return None

# ============ داده‌ها و فونت‌ها ============
DEFAULT_PALETTE = [
    ("سفید", "#FFFFFF"), ("مشکی", "#000000"), ("قرمز", "#F43F5E"), ("آبی", "#3B82F6"),
    ("سبز", "#22C55E"), ("زرد", "#EAB308"), ("بنفش", "#8B5CF6"), ("نارنجی", "#F97316"),
]
FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
LOCAL_FONT_FILES = {
    "Vazirmatn": ["Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf"],
    "Default": ["Vazirmatn-Regular.ttf"],
}
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
def resolve_font_path(text: str = "") -> str:
    if text and re.search(r'[\u0600-\u06ff]', text):
        return _LOCAL_FONTS.get("Vazirmatn", "")
    return _LOCAL_FONTS.get("Default", "")

# ============ رندر تصویر/استیکر ============
CANVAS = (512, 512)
def _prepare_text(text: str) -> str:
    if not text: return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def _parse_hex(hx: str) -> Tuple[int, int, int, int]:
    hx = (hx or "#ffffff").strip().lstrip("#")
    if len(hx) == 3: r, g, b = [int(c * 2, 16) for c in hx]
    else: r, g, b = int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)
    return (r, g, b, 255)

def render_image(text: str, v_pos: str, h_pos: str, color_hex: str, size_key: str, bg_mode: str = "transparent", bg_photo: Optional[bytes] = None) -> bytes:
    W, H = CANVAS
    if bg_photo:
        try: img = Image.open(BytesIO(bg_photo)).convert("RGBA").resize((W, H))
        except: img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    else:
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)
    color = _parse_hex(color_hex)
    padding = 40
    box_w, box_h = W - 2 * padding, H - 2 * padding
    size_map = {"small": 64, "medium": 96, "large": 128}
    base_size = size_map.get(size_key, 96)

    font_path = resolve_font_path(text)
    txt = _prepare_text(text)
    
    try:
        font = ImageFont.truetype(font_path, size=base_size) if font_path else ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), txt, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    if v_pos == "top": y = padding
    elif v_pos == "bottom": y = H - padding - text_height
    else: y = (H - text_height) / 2

    if h_pos == "left": x = padding
    elif h_pos == "right": x = W - padding - text_width
    else: x = W / 2

    draw.text((x, y), txt, font=font, fill=color, anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 220))

    buf = BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()

# ============ تابع کمکی کیبورد ============
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
        if current_pack and pack["short_name"] == current_pack["short_name"]: continue
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

def ai_color_kb():
    kb = InlineKeyboardBuilder()
    for name, hx in DEFAULT_PALETTE:
        kb.button(text=name, callback_data=f"ai:color:{hx}")
    kb.adjust(4)
    return kb.as_markup()

def ai_size_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="کوچک", callback_data="ai:size:small")
    kb.button(text="متوسط", callback_data="ai:size:medium")
    kb.button(text="بزرگ", callback_data="ai:size:large")
    kb.adjust(3)
    return kb.as_markup()

def admin_panel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="ارسال پیام همگانی", callback_data="admin:broadcast")
    kb.button(text="ارسال به کاربر خاص", callback_data="admin:dm_prompt")
    kb.button(text="تغییر سهمیه کاربر", callback_data="admin:quota_prompt")
    kb.adjust(1)
    return kb.as_markup()

# ============ تابع اصلی ثبت هندلرها ============
def register_handlers(dp: Dispatcher):
    router = Router()
    
    @router.message(CommandStart())
    async def on_start(message: types.Message, bot: Bot):
        is_member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=message.from_user.id)
        if not is_member:
            kb = InlineKeyboardBuilder()
            kb.button(text="عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
            kb.button(text="بررسی عضویت", callback_data="check_membership")
            kb.adjust(1)
            await message.answer(f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.\n\nپس از عضویت، روی دکمه «بررسی عضویت» کلیک کنید.", reply_markup=kb.as_markup())
            return

        is_admin = (message.from_user.id == ADMIN_ID)
        kb = main_menu_kb(is_admin)
        await message.answer("سلام! خوش آمدید\nیکی از گزینه‌های زیر رو انتخاب کن:", reply_markup=kb)

    @router.callback_query(F.data == "check_membership")
    async def on_check_membership(cb: types.CallbackQuery, bot: Bot):
        is_member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=cb.from_user.id)
        if is_member:
            kb = main_menu_kb(cb.from_user.id == ADMIN_ID)
            await cb.message.edit_text("عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.", reply_markup=kb.as_markup())
        else:
            await cb.answer("شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
        await cb.answer()

    @router.callback_query(F.data == "menu:home")
    async def on_home(cb: types.CallbackQuery, bot: Bot):
        kb = main_menu_kb(cb.from_user.id == ADMIN_ID)
        await cb.message.edit_text("منوی اصلی:", reply_markup=kb.as_markup())
        await cb.answer()

    @router.callback_query(F.data == "menu:help")
    async def on_help(cb: types.CallbackQuery, bot: Bot):
        help_text = "راهنما\n\n• استیکر ساده: ساخت استیکر با تنظیمات سریع\n• استیکر ساز پیشرفته: ساخت استیکر با تنظیمات پیشرفته\n• سهمیه امروز: محدودیت استفاده روزانه\n• پشتیبانی: ارتباط با ادمین"
        await cb.message.edit_text(help_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()

    @router.callback_query(F.data == "menu:support")
    async def on_support(cb: types.CallbackQuery, bot: Bot):
        await cb.message.edit_text(f"پشتیبانی: {SUPPORT_USERNAME}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()

    @router.callback_query(F.data == "menu:quota")
    async def on_quota(cb: types.CallbackQuery, bot: Bot):
        u = user(cb.from_user.id)
        is_admin = (cb.from_user.id == ADMIN_ID)
        left = _quota_left(u, is_admin)
        quota_txt = "نامحدود" if is_admin else f"{left} از {u.get('daily_limit', DAILY_LIMIT)}"
        await cb.message.edit_text(f"سهمیه امروز: {quota_txt}", reply_markup=back_to_menu_kb(is_admin))
        await cb.answer()

    @router.callback_query(F.data == "menu:simple")
    async def on_simple(cb: types.CallbackQuery, bot: Bot):
        s = sess(cb.from_user.id)
        uid = cb.from_user.id
        user_packs = get_user_packs(uid)
        if user_packs:
            s["pack_wizard"] = {"mode": "simple"}
            kb = pack_selection_kb(uid, "simple")
            await cb.message.edit_text("می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟", reply_markup=kb.as_markup())
        else:
            s["pack_wizard"] = {"step": "awaiting_name", "mode": "simple"}
            rules_text = "نام پک را بنویس (مثال: my_stickers):\n\n• فقط حروف انگلیسی کوچک، عدد و زیرخط\n• باید با حرف شروع شود\n• نباید با زیرخط تمام شود\n• نباید دو زیرخط پشت سر هم داشته باشد\n• حداکثر ۵۰ کاراکتر"
            await cb.message.edit_text(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()

    @router.callback_query(F.data == "menu:ai")
    async def on_ai(cb: types.CallbackQuery, bot: Bot):
        u = user(cb.from_user.id)
        is_admin = (cb.from_user.id == ADMIN_ID)
        left = _quota_left(u, is_admin)
        if left <= 0 and not is_admin:
            await cb.answer("سهمیه امروز تمام شد!", show_alert=True)
            return
        s = sess(cb.from_user.id)
        uid = cb.from_user.id
        user_packs = get_user_packs(uid)
        if user_packs:
            s["pack_wizard"] = {"mode": "ai"}
            kb = pack_selection_kb(uid, "ai")
            await cb.message.edit_text("می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟", reply_markup=kb.as_markup())
        else:
            s["pack_wizard"] = {"step": "awaiting_name", "mode": "ai"}
            rules_text = "نام پک را بنویس (مثال: my_stickers):\n\n• فقط حروف انگلیسی کوچک، عدد و زیرخط\n• باید با حرف شروع شود\n• نباید با زیرخط تمام شود\n• نباید دو زیرخط پشت سر هم داشته باشد\n• حداکثر ۵۰ کاراکتر"
            await cb.message.edit_text(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()

    @router.callback_query(F.data.startswith('pack:'))
    async def pack_callbacks(cb: types.CallbackQuery, bot: Bot):
        s = sess(cb.from_user.id)
        uid = cb.from_user.id
        parts = cb.data.split(':')
        
        if parts[1] == 'select':
            pack_short_name = parts[2]
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
                    await cb.message.edit_text(f"پک «{selected_pack['name']}» انتخاب شد.\n\nمتن استیکر ساده رو بفرست:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
                elif mode == "ai":
                    s["mode"] = "ai"
                    s["ai"] = {"text": None, "v_pos": "center", "h_pos": "center", "font": "Default", "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None}
                    await cb.message.edit_text(f"پک «{selected_pack['name']}» انتخاب شد.\n\nنوع استیکر پیشرفته را انتخاب کنید:", reply_markup=ai_type_kb())
        elif parts[1] == 'new':
            mode = parts[2]
            s["pack_wizard"] = {"step": "awaiting_name", "mode": mode}
            rules_text = "برای ایجاد پک جدید، یک نام انگلیسی ارسال کنید.\n\n• فقط حروف انگلیسی کوچک، عدد و زیرخط\n• حداکثر ۵۰ کاراکتر"
            await cb.message.edit_text(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        
        await cb.answer()

    @router.callback_query(F.data.startswith('simple:bg:'))
    async def simple_bg_callback(cb: types.CallbackQuery, bot: Bot):
        s = sess(cb.from_user.id)["simple"]
        mode = cb.data.split(':')[-1]
        if mode == "photo_prompt":
            s["awaiting_bg_photo"] = True
            await cb.message.edit_text("عکس مورد نظر برای پس‌زمینه را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        else:
            s["bg_mode"] = mode
            s["bg_photo_bytes"] = None
            if s.get("text"):
                img = render_image(text=s["text"], v_pos="center", h_pos="center", font_key="Default", color_hex="#FFFFFF", size_key="medium", bg_mode=mode, bg_photo=s.get("bg_photo_bytes"))
                await bot.send_photo(cb.message.chat.id, photo=img, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
        await cb.answer()

    @router.callback_query(F.data.startswith('simple:'))
    async def simple_action_callback(cb: types.CallbackQuery, bot: Bot):
        s = sess(cb.from_user.id)
        action = cb.data.split(':')[1]
        if action == 'confirm':
            simple_data = s["simple"]
            img = render_image(text=simple_data["text"] or "سلام", v_pos="center", h_pos="center", font_key="Default", color_hex="#FFFFFF", size_key="medium", bg_mode=simple_data.get("bg_mode") or "transparent", bg_photo=simple_data.get("bg_photo_bytes"))
            s["last_sticker"] = img
            await bot.send_sticker(cb.message.chat.id, sticker=img)
            await bot.send_message(cb.message.chat.id, "از این استیکر راضی بودی؟", reply_markup=rate_kb())
        elif action == 'edit':
            await cb.message.edit_text("پس‌زمینه رو انتخاب کن:", reply_markup=simple_bg_kb())
        await cb.answer()

    @router.callback_query(F.data.startswith('ai:'))
    async def ai_callbacks(cb: types.CallbackQuery, bot: Bot):
        s = sess(cb.from_user.id)
        parts = cb.data.split(':')
        
        if parts[1] == 'type':
            s["ai"]["sticker_type"] = parts[2]
            if parts[2] == 'image':
                await cb.message.edit_text("منبع استیکر تصویری را انتخاب کنید:", reply_markup=ai_image_source_kb())
            elif parts[2] == 'video':
                await cb.message.edit_text("یک فایل ویدیو ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        
        elif parts[1] == 'source':
            if parts[2] == 'text':
                await cb.message.edit_text("متن استیکر را بفرست:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
            elif parts[2] == 'photo':
                s["ai"]["awaiting_bg_photo"] = True
                await cb.message.edit_text("عکس را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        
        elif parts[1] in ['vpos', 'hpos', 'color', 'size']:
            if parts[1] == 'vpos': s["ai"]["v_pos"] = parts[2]; await cb.message.edit_text("موقعیت افقی متن:", reply_markup=ai_hpos_kb())
            elif parts[1] == 'hpos': s["ai"]["h_pos"] = parts[2]; await cb.message.edit_text("رنگ متن:", reply_markup=ai_color_kb())
            elif parts[1] == 'color': s["ai"]["color"] = parts[2]; await cb.message.edit_text("اندازه فونت:", reply_markup=ai_size_kb())
            elif parts[1] == 'size':
                s["ai"]["size"] = parts[2]
                ai_data = s["ai"]
                img = render_image(text=ai_data.get("text") or "متن ساده", v_pos=ai_data["v_pos"], h_pos=ai_data["h_pos"], font_key="Default", color_hex=ai_data["color"], size_key=parts[2], bg_mode="transparent", bg_photo=ai_data.get("bg_photo_bytes"))
                await bot.send_photo(cb.message.chat.id, photo=img, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("ai"))
        
        elif parts[1] in ['confirm', 'edit']:
            if parts[1] == 'confirm':
                u = user(cb.from_user.id)
                is_admin = (cb.from_user.id == ADMIN_ID)
                left = _quota_left(u, is_admin)
                if left <= 0 and not is_admin:
                    await cb.answer("سهمیه تمام شد!", show_alert=True)
                    return
                ai_data = s["ai"]
                img = render_image(text=ai_data.get("text") or "سلام", v_pos=ai_data["v_pos"], h_pos=ai_data["h_pos"], font_key="Default", color_hex=ai_data["color"], size_key=ai_data["size"], bg_mode="transparent", bg_photo=ai_data.get("bg_photo_bytes"))
                s["last_sticker"] = img
                if not is_admin: u["ai_used"] = int(u.get("ai_used", 0)) + 1
                await bot.send_sticker(cb.message.chat.id, sticker=img)
                await bot.send_message(cb.message.chat.id, "از این استیکر راضی بودی؟", reply_markup=rate_kb())
            elif parts[1] == 'edit':
                await cb.message.edit_text("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
        
        await cb.answer()

    @router.callback_query(F.data.startswith('rate:'))
    async def rate_callbacks(cb: types.CallbackQuery, bot: Bot):
        s = sess(cb.from_user.id)
        if cb.data.split(':')[1] == 'yes':
            sticker_bytes = s.get("last_sticker")
            pack_short_name = s.get("current_pack_short_name")
            pack_title = s.get("current_pack_title")
            if not sticker_bytes or not pack_short_name:
                await cb.answer("خطایی در پیدا کردن پک یا استیکر رخ داد.", show_alert=True)
                return
            try:
                await asyncio.sleep(1.5)
                await bot.add_sticker_to_set(cb.from_user.id, pack_short_name, types.InputSticker(sticker=sticker_bytes, emoji_list=['😂']))
                pack_link = f"https://t.me/addstickers/{pack_short_name}"
                await cb.message.edit_text(f"استیکر با موفقیت به پک «{pack_title}» اضافه شد.\n\n{pack_link}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
            except Exception as e:
                await cb.message.edit_text(f"خطا در افزودن استیکر به پک: {e}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        else:
            s["await_feedback"] = True
            await cb.message.edit_text("چه چیزی رو دوست نداشتی؟", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()

    @router.message_handler(content_types=['text', 'photo', 'video', 'document'])
    async def handle_content(message: types.Message, bot: Bot):
        s = sess(message.from_user.id)
        uid = message.from_user.id
        is_admin = (uid == ADMIN_ID)

        # Feedback handler
        if s.get("await_feedback") and message.text:
            s["await_feedback"] = False
            await bot.reply_to(message, "ممنون از بازخوردت", reply_markup=back_to_menu_kb(is_admin))
            return

        # Pack creation wizard
        pack_wizard = s.get("pack_wizard", {})
        if pack_wizard.get("step") == "awaiting_name" and message.text:
            global BOT_USERNAME
            if not BOT_USERNAME:
                bot_info = await bot.get_me()
                BOT_USERNAME = bot_info.username
            pack_name = message.text.strip()
            pack_name_lower = pack_name.lower()
            if any(word in pack_name_lower for word in FORBIDDEN_WORDS):
                await bot.reply_to(message, "نام پک انتخاب شده نامناسب است.", reply_markup=back_to_menu_kb(is_admin))
                return
            if not re.match(r'^[a-z0-9_]{1,50}$', pack_name) or pack_name.startswith('_') or pack_name.endswith('_') or '__' in pack_name:
                await bot.reply_to(message, "نام پک نامعتبر است. لطفا طبق قوانین یک نام جدید انتخاب کنید.", reply_markup=back_to_menu_kb(is_admin))
                return
            short_name = f"{pack_name}_by_{BOT_USERNAME}"
            mode = pack_wizard.get("mode")
            try:
                await bot.create_new_sticker_set(uid, short_name, pack_name, types.InputSticker(sticker=render_image("First", "center", "center", "Default", "#FFFFFF", "medium"), emoji_list=['🎉']))
                add_user_pack(uid, pack_name, short_name)
                s["current_pack_short_name"] = short_name
                s["current_pack_title"] = pack_name
                s["pack_wizard"] = {}
                await bot.reply_to(message, f"پک استیکر «{pack_name}» با موفقیت ساخته شد!\n\nhttps://t.me/addstickers/{short_name}\n\nحالا استیکر بعدی خود را بسازید.")
                if mode == "simple":
                    s["mode"] = "simple"; s["simple"] = {"text": None, "bg_mode": "transparent", "bg_photo_bytes": None}
                    await bot.send_message(message.chat.id, "متن استیکر ساده رو بفرست:")
                elif mode == "ai":
                    s["mode"] = "ai"; s["ai"] = {"text": None, "v_pos": "center", "h_pos": "center", "font": "Default", "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None}
                    await bot.send_message(message.chat.id, "نوع استیکر پیشرفته را انتخاب کنید:", reply_markup=ai_type_kb())
            except Exception as e:
                await bot.reply_to(message, f"خطا در ساخت پک: {e}")
            return

        # Simple sticker logic
        if s["mode"] == "simple":
            if s["simple"].get("awaiting_bg_photo") and message.photo:
                photo = message.photo[-1]
                file_info = await bot.get_file(photo.file_id)
                downloaded_file = await bot.download_file(file_info.file_path)
                s["simple"]["bg_photo_bytes"] = downloaded_file
                s["simple"]["awaiting_bg_photo"] = False
                await bot.send_message(message.chat.id, "عکس به عنوان پس‌زمینه تنظیم شد. حالا متن استیکر را بفرستید.")
                return
            if message.text:
                s["simple"]["text"] = message.text
                img = render_image(text=message.text, v_pos="center", h_pos="center", font_key="Default", color_hex="#FFFFFF", size_key="medium", bg_mode=s["simple"].get("bg_mode", "transparent"), bg_photo=s["simple"].get("bg_photo_bytes"))
                await bot.send_photo(message.chat.id, photo=img, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
            return

        # AI sticker logic
        if s["mode"] == "ai":
            if s["ai"].get("awaiting_bg_photo") and message.photo:
                photo = message.photo[-1]
                file_info = await bot.get_file(photo.file_id)
                downloaded_file = await bot.download_file(file_info.file_path)
                s["ai"]["bg_photo_bytes"] = downloaded_file
                s["ai"]["awaiting_bg_photo"] = False
                await bot.send_message(message.chat.id, "عکس به عنوان پس‌زمینه تنظیم شد. حالا موقعیت متن را انتخاب کنید:", reply_markup=ai_vpos_kb())
                return
            if s["ai"].get("sticker_type") == "image" and message.text:
                s["ai"]["text"] = message.text
                await bot.send_message(message.chat.id, "موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
                return
            if s["ai"].get("sticker_type") == "video" and message.video:
                await bot.reply_to(message, "پردازش ویدیو در حال حاضر پشتیبانی نمی‌شود.")
                return

    dp.include_router(router)
