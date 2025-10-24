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
import telebot
from telebot import types
from telebot.util import quick_markup
from telebot.types import BotCommand

# =============== پیکربندی ===============
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE").strip()
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
DEFAULT_PALETTE = [("سفید", "#FFFFFF"), ("مشکی", "#000000"), ("قرمز", "#F43F5E"), ("آبی", "#3B82F6"), ("سبز", "#22C55E"), ("زرد", "#EAB308"), ("بنفش", "#8B5CF6"), ("نارنجی", "#F97316")]
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

# ============ تابع بررسی عضویت ============
async def check_membership(bot: telebot.TeleBot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

# ============ توابع کمکی کیبورد ============
def main_menu_kb(is_admin: bool = False):
    buttons = [
        types.InlineKeyboardButton("استیکر ساده", callback_data="menu:simple"),
        types.InlineKeyboardButton("استیکر ساز پیشرفته", callback_data="menu:ai"),
        types.InlineKeyboardButton("سهمیه امروز", callback_data="menu:quota"),
        types.InlineKeyboardButton("راهنما", callback_data="menu:help"),
        types.InlineKeyboardButton("پشتیبانی", callback_data="menu:support"),
    ]
    if is_admin:
        buttons.append(types.InlineKeyboardButton("پنل ادمین", callback_data="menu:admin"))
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    return keyboard

def back_to_menu_kb(is_admin: bool = False):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("بازگشت به منو", callback_data="menu:home"))
    if is_admin:
        keyboard.add(types.InlineKeyboardButton("پنل ادمین", callback_data="menu:admin"))
    return keyboard

def simple_bg_kb():
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton("شفاف", callback_data="simple:bg:transparent"),
        types.InlineKeyboardButton("پیش‌فرض", callback_data="simple:bg:default"),
        types.InlineKeyboardButton("ارسال عکس", callback_data="simple:bg:photo_prompt")
    )
    return keyboard

def after_preview_kb(prefix: str):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("تایید", callback_data=f"{prefix}:confirm"),
        types.InlineKeyboardButton("ویرایش", callback_data=f"{prefix}:edit"),
        types.InlineKeyboardButton("بازگشت", callback_data="menu:home")
    )
    return keyboard

def rate_kb():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("بله", callback_data="rate:yes"),
        types.InlineKeyboardButton("خیر", callback_data="rate:no"),
        types.InlineKeyboardButton("ساخت پک جدید", callback_data="pack:start_creation")
    )
    return keyboard

def pack_selection_kb(uid: int, mode: str):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    user_packs = get_user_packs(uid)
    current_pack = get_current_pack(uid)
    if current_pack:
        keyboard.add(types.InlineKeyboardButton(f"📦 {current_pack['name']} (فعلی)", callback_data=f"pack:select:{current_pack['short_name']}"))
    for pack in user_packs:
        if current_pack and pack["short_name"] == current_pack["short_name"]: continue
        keyboard.add(types.InlineKeyboardButton(f"📦 {pack['name']}", callback_data=f"pack:select:{pack['short_name']}"))
    keyboard.add(types.InlineKeyboardButton("➕ ساخت پک جدید", callback_data=f"pack:new:{mode}"))
    return keyboard

def ai_type_kb():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("استیکر تصویری", callback_data="ai:type:image"),
        types.InlineKeyboardButton("استیکر ویدیویی", callback_data="ai:type:video")
    )
    return keyboard

def ai_vpos_kb():
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton("بالا", callback_data="ai:vpos:top"),
        types.InlineKeyboardButton("وسط", callback_data="ai:vpos:center"),
        types.InlineKeyboardButton("پایین", callback_data="ai:vpos:bottom")
    )
    return keyboard

def ai_hpos_kb():
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        types.InlineKeyboardButton("چپ", callback_data="ai:hpos:left"),
        types.InlineKeyboardButton("وسط", callback_data="ai:hpos:center"),
        types.InlineKeyboardButton("راست", callback_data="ai:hpos:right")
    )
    return keyboard

def admin_panel_kb():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("ارسال پیام همگانی", callback_data="admin:broadcast"),
        types.InlineKeyboardButton("ارسال به کاربر خاص", callback_data="admin:dm_prompt"),
        types.InlineKeyboardButton("تغییر سهمیه کاربر", callback_data="admin:quota_prompt")
    )
    return keyboard

# ============ تابع اصلی ثبت هندلرها ============
def register_handlers(bot: telebot.TeleBot):
    """
    این تابع تمام هندلرهای ربات را به نمونه ربات ثبت می‌کند.
    """
    @bot.message_handler(commands=['start'])
    async def start_command(message: types.Message):
        is_member = await check_membership(bot, message.from_user.id)
        if not is_member:
            kb = quick_markup({
                "عضویت در کانال": {'url': f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"},
                "بررسی عضویت": {'callback_data': 'check_membership'}
            }, row_width=1)
            await bot.reply_to(message, f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.\n\nپس از عضویت، روی دکمه «بررسی عضویت» کلیک کنید.", reply_markup=kb)
            return

        is_admin = (message.from_user.id == ADMIN_ID)
        kb = main_menu_kb(is_admin)
        await bot.reply_to(message, "سلام! خوش آمدید\nیکی از گزینه‌های زیر رو انتخاب کن:", reply_markup=kb)

    @bot.callback_query_handler(func=lambda call: call.data == 'check_membership')
    async def check_membership_callback(call: types.CallbackQuery):
        is_member = await check_membership(bot, call.from_user.id)
        if is_member:
            kb = main_menu_kb(call.from_user.id == ADMIN_ID)
            await bot.edit_message_text("عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.", call.message.chat.id, call.message.message_id, reply_markup=kb)
        else:
            await bot.answer_callback_query(call.id, "شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == 'menu:home')
    async def home_callback(call: types.CallbackQuery):
        kb = main_menu_kb(call.from_user.id == ADMIN_ID)
        await bot.edit_message_text("منوی اصلی:", call.message.chat.id, call.message.message_id, reply_markup=kb)
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'menu:help')
    async def help_callback(call: types.CallbackQuery):
        help_text = "راهنما\n\n• استیکر ساده: ساخت استیکر با تنظیمات سریع\n• استیکر ساز پیشرفته: ساخت استیکر با تنظیمات پیشرفته\n• سهمیه امروز: محدودیت استفاده روزانه\n• پشتیبانی: ارتباط با ادمین"
        await bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(call.from_user.id == ADMIN_ID))
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'menu:support')
    async def support_callback(call: types.CallbackQuery):
        await bot.edit_message_text(f"پشتیبانی: {SUPPORT_USERNAME}", call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(call.from_user.id == ADMIN_ID))
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'menu:quota')
    async def quota_callback(call: types.CallbackQuery):
        u = user(call.from_user.id)
        is_admin = (call.from_user.id == ADMIN_ID)
        left = _quota_left(u, is_admin)
        quota_txt = "نامحدود" if is_admin else f"{left} از {u.get('daily_limit', DAILY_LIMIT)}"
        await bot.edit_message_text(f"سهمیه امروز: {quota_txt}", call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(is_admin))
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'menu:simple')
    async def simple_callback(call: types.CallbackQuery):
        s = sess(call.from_user.id)
        uid = call.from_user.id
        user_packs = get_user_packs(uid)
        if user_packs:
            s["pack_wizard"] = {"mode": "simple"}
            kb = pack_selection_kb(uid, "simple")
            await bot.edit_message_text("می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟", call.message.chat.id, call.message.message_id, reply_markup=kb)
        else:
            s["pack_wizard"] = {"step": "awaiting_name", "mode": "simple"}
            rules_text = "نام پک را بنویس (مثال: my_stickers):\n\n• فقط حروف انگلیسی کوچک، عدد و زیرخط\n• باید با حرف شروع شود\n• نباید با زیرخط تمام شود\n• نباید دو زیرخط پشت سر هم داشته باشد\n• حداکثر ۵۰ کاراکتر"
            await bot.edit_message_text(rules_text, call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(call.from_user.id == ADMIN_ID))
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'menu:ai')
    async def ai_callback(call: types.CallbackQuery):
        u = user(call.from_user.id)
        is_admin = (call.from_user.id == ADMIN_ID)
        left = _quota_left(u, is_admin)
        if left <= 0 and not is_admin:
            await bot.answer_callback_query(call.id, "سهمیه امروز تمام شد!", show_alert=True)
            return
        s = sess(call.from_user.id)
        uid = call.from_user.id
        user_packs = get_user_packs(uid)
        if user_packs:
            s["pack_wizard"] = {"mode": "ai"}
            kb = pack_selection_kb(uid, "ai")
            await bot.edit_message_text("می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟", call.message.chat.id, call.message.message_id, reply_markup=kb)
        else:
            s["pack_wizard"] = {"step": "awaiting_name", "mode": "ai"}
            rules_text = "نام پک را بنویس (مثال: my_stickers):\n\n• فقط حروف انگلیسی کوچک، عدد و زیرخط\n• باید با حرف شروع شود\n• نباید با زیرخط تمام شود\n• نباید دو زیرخط پشت سر هم داشته باشد\n• حداکثر ۵۰ کاراکتر"
            await bot.edit_message_text(rules_text, call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(call.from_user.id == ADMIN_ID))
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('pack:select:'))
    async def pack_select_callback(call: types.CallbackQuery):
        pack_short_name = call.data.split(':')[-1]
        uid = call.from_user.id
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
                await bot.edit_message_text(f"پک «{selected_pack['name']}» انتخاب شد.\n\nمتن استیکر ساده رو بفرست:", call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(call.from_user.id == ADMIN_ID))
            elif mode == "ai":
                s["mode"] = "ai"
                s["ai"] = {"text": None, "v_pos": "center", "h_pos": "center", "font": "Default", "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None}
                await bot.edit_message_text(f"پک «{selected_pack['name']}» انتخاب شد.\n\nنوع استیکر پیشرفته را انتخاب کنید:", call.message.chat.id, call.message.message_id, reply_markup=ai_type_kb())
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('simple:bg:'))
    async def simple_bg_callback(call: types.CallbackQuery):
        s = sess(call.from_user.id)["simple"]
        mode = call.data.split(':')[-1]
        if mode == "photo_prompt":
            s["awaiting_bg_photo"] = True
            await bot.edit_message_text("عکس مورد نظر برای پس‌زمینه را ارسال کنید:", call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(call.from_user.id == ADMIN_ID))
        else:
            s["bg_mode"] = mode
            s["bg_photo_bytes"] = None
            if s.get("text"):
                img = render_image(text=s["text"], v_pos="center", h_pos="center", font_key="Default", color_hex="#FFFFFF", size_key="medium", bg_mode=mode, bg_photo=s.get("bg_photo_bytes"))
                await bot.send_photo(call.message.chat.id, photo=img, caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'simple:confirm')
    async def simple_confirm_callback(call: types.CallbackQuery):
        s = sess(call.from_user.id)
        simple_data = s["simple"]
        img = render_image(text=simple_data["text"] or "سلام", v_pos="center", h_pos="center", font_key="Default", color_hex="#FFFFFF", size_key="medium", bg_mode=simple_data.get("bg_mode") or "transparent", bg_photo=simple_data.get("bg_photo_bytes"))
        s["last_sticker"] = img
        await bot.send_sticker(call.message.chat.id, sticker=img)
        await bot.send_message(call.message.chat.id, "از این استیکر راضی بودی؟", reply_markup=rate_kb())
        await bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'rate:yes')
    async def rate_yes_callback(call: types.CallbackQuery):
        s = sess(call.from_user.id)
        sticker_bytes = s.get("last_sticker")
        pack_short_name = s.get("current_pack_short_name")
        pack_title = s.get("current_pack_title")
        if not sticker_bytes or not pack_short_name:
            await bot.answer_callback_query(call.id, "خطایی در پیدا کردن پک یا استیکر رخ داد.", show_alert=True)
            return
        try:
            await asyncio.sleep(1.5) # تاخیر برای جلوگیری از محدودیت تلگرام
            await bot.add_sticker_to_set(call.from_user.id, pack_short_name, types.InputSticker(sticker=sticker_bytes, emoji='😂'))
            pack_link = f"https://t.me/addstickers/{pack_short_name}"
            await bot.edit_message_text(f"استیکر با موفقیت به پک «{pack_title}» اضافه شد.\n\n{pack_link}", call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(call.from_user.id == ADMIN_ID))
        except Exception as e:
            await bot.edit_message_text(f"خطا در افزودن استیکر به پک: {e}", call.message.chat.id, call.message.message_id, reply_markup=back_to_menu_kb(call.from_user.id == ADMIN_ID))
        await bot.answer_callback_query(call.id)

    @bot.message_handler(content_types=['text', 'photo'])
    async def handle_content(message: types.Message):
        s = sess(message.from_user.id)
        uid = message.from_user.id
        
        # منطق ساخت پک جدید
        pack_wizard = s.get("pack_wizard", {})
        if pack_wizard.get("step") == "awaiting_name" and message.text:
            global BOT_USERNAME
            if not BOT_USERNAME:
                bot_info = await bot.get_me()
                BOT_USERNAME = bot_info.username
            pack_name = message.text.strip()
            if not re.match(r'^[a-z0-9_]{1,50}$', pack_name) or pack_name.startswith('_') or pack_name.endswith('_') or '__' in pack_name:
                await bot.reply_to(message, "نام پک نامعتبر است. لطفا طبق قوانین یک نام جدید انتخاب کنید.", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
                return
            short_name = f"{pack_name}_by_{BOT_USERNAME}"
            mode = pack_wizard.get("mode")
            try:
                await bot.create_new_sticker_set(uid, short_name, pack_name, types.InputSticker(sticker=render_image("First", "center", "center", "Default", "#FFFFFF", "medium"), '🎉'))
                add_user_pack(uid, pack_name, short_name)
                s["current_pack_short_name"] = short_name
                s["current_pack_title"] = pack_name
                s["pack_wizard"] = {}
                await bot.reply_to(message, f"پک استیکر «{pack_name}» با موفقیت ساخته شد!\n\nhttps://t.me/addstickers/{short_name}\n\nحالا استیکر بعدی خود را بسازید.")
                if mode == "simple":
                    s["mode"] = "simple"
                    s["simple"] = {"text": None, "bg_mode": "transparent", "bg_photo_bytes": None}
                    await bot.send_message(message.chat.id, "متن استیکر ساده رو بفرست:")
                elif mode == "ai":
                    s["mode"] = "ai"
                    s["ai"] = {"text": None, "v_pos": "center", "h_pos": "center", "font": "Default", "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None}
                    await bot.send_message(message.chat.id, "نوع استیکر پیشرفته را انتخاب کنید:", reply_markup=ai_type_kb())
            except Exception as e:
                await bot.reply_to(message, f"خطا در ساخت پک: {e}")
            return

        # منطق استیکر ساده
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

        # منطق استیکر پیشرفته
        if s["mode"] == "ai":
            if message.text:
                s["ai"]["text"] = message.text
                await bot.send_message(message.chat.id, "موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
            return
