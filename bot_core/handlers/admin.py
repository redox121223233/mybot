from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery
from ..config import ADMIN_ID
from ..keyboards import admin_panel_kb, back_to_menu_kb
from ..services.storage import storage
from .common import safe_edit_text

router = Router()

def is_admin_active(message: Message) -> bool:
    s = storage.get_session(message.from_user.id)
    return bool(s.get("admin", {}).get("step"))

@router.callback_query(F.data == "admin:broadcast")
async def on_admin_broadcast_prompt(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    storage.update_session(cb.from_user.id, {"admin": {"step": "awaiting_broadcast"}})
    await safe_edit_text(cb, "متن پیام همگانی را بفرستید:", reply_markup=back_to_menu_kb(True))
    await cb.answer()

@router.callback_query(F.data == "admin:dm_prompt")
async def on_admin_dm_prompt(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    storage.update_session(cb.from_user.id, {"admin": {"step": "awaiting_dm_id"}})
    await safe_edit_text(cb, "آیدی عددی کاربر را بفرستید:", reply_markup=back_to_menu_kb(True))
    await cb.answer()

@router.message(F.from_user.id == ADMIN_ID, is_admin_active)
async def admin_message_handler(message: Message, bot: Bot):
    s = storage.get_session(message.from_user.id)
    admin_state = s.get("admin", {})
    step = admin_state.get("step")

    if step == "awaiting_broadcast":
        storage.update_session(message.from_user.id, {"admin": {}})
        await message.answer("در حال ارسال پیام همگانی...")
        users = storage.USERS.keys()
        count = 0
        for uid_str in users:
            try:
                await bot.send_message(int(uid_str), message.text)
                count += 1
            except Exception:
                pass
        await message.answer(f"پیام به {count} کاربر ارسال شد.", reply_markup=admin_panel_kb())

    elif step == "awaiting_dm_id":
        target_id = message.text.strip()
        if target_id.isdigit():
            storage.update_session(message.from_user.id, {"admin": {"step": "awaiting_dm_text", "target_id": int(target_id)}})
            await message.answer(f"حالا متن پیام برای کاربر {target_id} را بفرستید:")
        else:
            await message.answer("آیدی باید عددی باشد.")

    elif step == "awaiting_dm_text":
        target_id = admin_state.get("target_id")
        storage.update_session(message.from_user.id, {"admin": {}})
        try:
            await bot.send_message(target_id, message.text)
            await message.answer("پیام با موفقیت ارسال شد.", reply_markup=admin_panel_kb())
        except Exception as e:
            await message.answer(f"خطا در ارسال پیام: {e}", reply_markup=admin_panel_kb())
