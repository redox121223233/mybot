from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from ..config import ADMIN_ID, CHANNEL_USERNAME, SUPPORT_USERNAME, DAILY_LIMIT
from ..services.storage import storage
from ..utils.helpers import _quota_left, _fmt_eta, _seconds_to_reset
from ..keyboards import main_menu_kb, back_to_menu_kb, pack_selection_kb

router = Router()

async def check_channel_membership(bot: Bot, user_id: int) -> bool:
    if not CHANNEL_USERNAME:
        return True
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def require_channel_membership(message: Message, bot: Bot) -> bool:
    if await check_channel_membership(bot, message.from_user.id):
        return True

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
    kb.button(text="بررسی عضویت", callback_data="check_membership")
    kb.adjust(1)

    try:
        await message.answer(f"برای استفاده از ربات، باید در کانال {CHANNEL_USERNAME} عضو شوید.", reply_markup=kb.as_markup())
    except TelegramForbiddenError:
        print(f"User {message.from_user.id} has blocked the bot.")
    return False

async def safe_edit_text(cb: CallbackQuery, text: str, reply_markup=None, delete_if_no_text: bool = True):
    try:
        await cb.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "there is no text in the message to edit" in str(e) and delete_if_no_text:
            await cb.message.delete()
            await cb.message.answer(text, reply_markup=reply_markup)
        else:
            raise

@router.message(CommandStart())
async def on_start(message: Message, bot: Bot):
    if not await require_channel_membership(message, bot):
        return
    storage.reset_session(message.from_user.id)
    await message.answer("سلام! خوش آمدید\nیکی از گزینه‌های زیر رو انتخاب کن:", reply_markup=main_menu_kb(message.from_user.id == ADMIN_ID))

@router.callback_query(F.data == "check_membership")
async def on_check_membership(cb: CallbackQuery, bot: Bot):
    if await check_channel_membership(bot, cb.from_user.id):
        await cb.message.answer("عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.", reply_markup=main_menu_kb(cb.from_user.id == ADMIN_ID))
    else:
        await cb.answer("شما هنوز در کانال عضو نشده‌اید!", show_alert=True)
    await cb.answer()

@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
    storage.reset_session(cb.from_user.id)
    await safe_edit_text(cb, "منوی اصلی:", reply_markup=main_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("menu:"))
async def on_menu_selection(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return

    action = cb.data.split(":")[1]
    uid = cb.from_user.id
    is_admin = (uid == ADMIN_ID)
    s = storage.get_session(uid)
    u = storage.get_user(uid)

    if action in ["simple", "ai"]:
        if action == "ai" and _quota_left(u, is_admin) <= 0:
            await cb.answer("سهمیه امروز شما تمام شده است.", show_alert=True)
            return

        s["pack_wizard"] = {"mode": action}
        s["mode"] = action

        packs = storage.get_user_packs(uid)
        if packs:
            current_pack = storage.get_current_pack(uid)
            short_name = current_pack["short_name"] if current_pack else None
            await safe_edit_text(cb, "استیکر را به کدام پک اضافه می‌کنید؟", reply_markup=pack_selection_kb(uid, packs, short_name, action))
        else:
            s["pack_wizard"]["step"] = "awaiting_name"
            await safe_edit_text(cb, "برای ساخت پک جدید، یک نام انگلیسی ارسال کنید.", reply_markup=back_to_menu_kb(is_admin))

    elif action == "quota":
        left = _quota_left(u, is_admin)
        if is_admin:
            quota_text = "سهمیه امروز شما: نامحدود"
        else:
            limit = u.get("daily_limit") or DAILY_LIMIT
            quota_text = f"سهمیه امروز شما: {left} از {limit}"
            if left <= 0:
                time_left = _fmt_eta(_seconds_to_reset(u))
                quota_text += f"\n\nزمان باقی‌مانده تا سهمیه بعدی: **{time_left}**"
        await safe_edit_text(cb, quota_text, reply_markup=back_to_menu_kb(is_admin))

    elif action == "help":
        help_text = """🤖 *راهنمای استفاده از ربات استیکر‌ساز*

📝 *ساخت استیکر ساده:*
1. گزینه 🎨 *ساخت استیکر ساده* را انتخاب کنید
2. یک پک استیکر موجود را انتخاب کرده یا پک جدید بسازید
3. متن مورد نظر خود را ارسال کنید
4. پس‌زمینه را انتخاب کنید (شفاف، رنگی یا عکس)
5. استیکر را تایید و به پک اضافه کنید

🎨 *ساخت استیکر هوشمند (AI):*
1. گزینه 🧠 *ساخت استیکر هوشمند* را انتخاب کنید
2. نوع استیکر را انتخاب کنید (متحرک یا ثابت)
3. منبع را انتخاب کنید (متن یا عکس)
4. تنظیمات دلخواه را اعمال کنید
5. استیکر نهایی را تایید کنید

📊 *سهمیه روزانه:*
• هر کاربر معمولی: محدودیت روزانه استیکر هوشمند
• ادمین: استفاده نامحدود از تمام امکانات
• سهمیه هر ۲۴ ساعت یکبار شارژ می‌شود

💡 *نکات مهم:*
• نام پک باید فقط شامل حروف انگلیسی، عدد و خط تیره باشد
• حداقل طول نام پک: ۳ کاراکتر
• حداکثر طول نام پک: ۵۰ کاراکتر
• برای استفاده از ربات، عضو کانال ما باشید

❓ *سوالات متداول:*
Q: چطور استیکر موجود را ویرایش کنم؟
A: متاسفانه امکان ویرایش استیکر وجود ندارد، باید استیکر جدید بسازید

Q: چرا نمی‌توانم استیکر هوشمند بسازم؟
A: ممکن است سهمیه روزانه شما تمام شده باشد

Q: چند پک استیکر می‌توانم بسازم؟
A: تعداد پک‌ها محدودیت خاصی ندارد

🆘 *برای دریافت پشتیبانی:* گزینه پشتیبانی را انتخاب کنید"""
        await safe_edit_text(cb, help_text, reply_markup=back_to_menu_kb(is_admin))

    elif action == "support":
        await safe_edit_text(cb, f"پشتیبانی: {SUPPORT_USERNAME}", reply_markup=back_to_menu_kb(is_admin))

    elif action == "admin" and is_admin:
        from ..keyboards import admin_panel_kb
        await safe_edit_text(cb, "پنل ادمین:", reply_markup=admin_panel_kb())

    await cb.answer()
