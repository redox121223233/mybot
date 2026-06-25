from aiogram.utils.keyboard import InlineKeyboardBuilder
from .config import DEFAULT_PALETTE

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

def pack_selection_kb(uid: int, packs: list, current_pack_short_name: str, mode: str):
    kb = InlineKeyboardBuilder()
    current_pack = next((p for p in packs if p["short_name"] == current_pack_short_name), None)
    if current_pack:
        kb.button(text=f"📦 {current_pack['name']} (فعلی)", callback_data=f"pack:select:{current_pack['short_name']}:{mode}")
    for pack in packs:
        if not current_pack or pack["short_name"] != current_pack["short_name"]:
            kb.button(text=f"📦 {pack['name']}", callback_data=f"pack:select:{pack['short_name']}:{mode}")
    kb.button(text="➕ ساخت پک جدید", callback_data=f"pack:new:{mode}")
    kb.adjust(1)
    return kb.as_markup()

def ai_type_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="استیکر تصویری", callback_data="ai:type:image")
    kb.button(text="استیکر ویدیویی", callback_data="ai:type:video")
    kb.adjust(1)
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

def ai_color_kb():
    kb = InlineKeyboardBuilder()
    for name, hex_code in DEFAULT_PALETTE:
        kb.button(text=name, callback_data=f"ai:color:{hex_code}")
    kb.adjust(4)
    return kb.as_markup()

def ai_size_kb():
    kb = InlineKeyboardBuilder()
    for label, value in [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]:
        kb.button(text=label, callback_data=f"ai:size:{value}")
    kb.adjust(3)
    return kb.as_markup()

def admin_panel_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="ارسال پیام همگانی", callback_data="admin:broadcast")
    kb.button(text="ارسال به کاربر خاص", callback_data="admin:dm_prompt")
    kb.button(text="تغییر سهمیه کاربر", callback_data="admin:quota_prompt")
    kb.adjust(1)
    return kb.as_markup()
