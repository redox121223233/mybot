# نسخه حداقلی برای تست نهایی
from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart

# آیدی ادمین را اینجا قرار دهید
ADMIN_ID = 6053579919

router = Router()

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

# هندلر استارت - هیچ API Call اضافه‌ای ندارد
@router.message(CommandStart())
async def on_start(message: types.Message):
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "سلام! خوش آمدید (نسخه تست)\n"
        "این نسخه برای عیب‌یابی است.\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=main_menu_kb(is_admin)
    )

# هندلر بازگشت به منو
@router.callback_query(F.data == "menu:home")
async def on_home(cb: types.CallbackQuery):
    is_admin = (cb.from_user.id == ADMIN_ID)
    await cb.message.answer("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
    await cb.answer()

# هندلر راهنما
@router.callback_query(F.data == "menu:help")
async def on_help(cb: types.CallbackQuery):
    await cb.message.answer(
        "این یک راهنمای تست است.\n"
        "اگر این پیام را دریافت کنید، یعنی ساختار اصلی ربات در Vercel کار می‌کند."
    )
    await cb.answer()

# هندلر پشتیبانی
@router.callback_query(F.data == "menu:support")
async def on_support(cb: types.CallbackQuery):
    await cb.message.answer("پشتیبانی: @onedaytoalive")
    await cb.answer()

# هندلر سهمیه
@router.callback_query(F.data == "menu:quota")
async def on_quota(cb: types.CallbackQuery):
    await cb.message.answer("سهمیه شما نامحدود است (نسخه تست).")
    await cb.answer()

# هندلرهای خالی برای جلوگیری از خطای "not handled"
@router.callback_query(F.data.startswith("menu:"))
async def on_other_menu(cb: types.CallbackQuery):
    await cb.answer("این قابلیت در نسخه تست فعال نیست.", show_alert=True)
