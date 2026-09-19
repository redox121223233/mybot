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

@router.callback_query(F.data == "admin:stats")
async def on_admin_stats(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    total_users = len(storage.USERS)
    total_packs = sum(len(u.get("packs", [])) for u in storage.USERS.values())
    total_ai_used = sum(u.get("ai_used", 0) for u in storage.USERS.values())
    active_sessions = len(storage.SESSIONS)

    stats_text = (
        "📊 **آمار و اطلاعات ربات:**\n\n"
        f"👥 **تعداد کل کاربران ثبت‌شده:** `{total_users}` نفر\n"
        f"📦 **تعداد کل پک‌های ساخته‌شده:** `{total_packs}` پک\n"
        f"🎨 **تعداد استیکرهای پیشرفته ساخته‌شده:** `{total_ai_used}` استیکر\n"
        f"💬 **نشست‌های فعال:** `{active_sessions}` کاربر"
    )
    await safe_edit_text(cb, stats_text, reply_markup=admin_panel_kb())
    await cb.answer()

@router.callback_query(F.data.in_(["admin:broadcast", "admin:broadcast_prompt"]))
async def on_admin_broadcast_prompt(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    storage.update_session(cb.from_user.id, {"admin": {"step": "awaiting_broadcast"}})
    await safe_edit_text(cb, "📢 **ارسال پیام همگانی:**\n\nلطفاً پیام خود را ارسال کنید (می‌توانید متن، عکس، ویدیو، گیف یا ویس بفرستید):", reply_markup=back_to_menu_kb(True))
    await cb.answer()

@router.callback_query(F.data == "admin:dm_prompt")
async def on_admin_dm_prompt(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    storage.update_session(cb.from_user.id, {"admin": {"step": "awaiting_dm_id"}})
    await safe_edit_text(cb, "✉️ **ارسال پیام به کاربر خاص:**\n\nلطفاً آیدی عددی کاربر مورد نظر را بفرستید:", reply_markup=back_to_menu_kb(True))
    await cb.answer()

@router.callback_query(F.data == "admin:quota_prompt")
async def on_admin_quota_prompt(cb: CallbackQuery):
    if cb.from_user.id != ADMIN_ID: return
    storage.update_session(cb.from_user.id, {"admin": {"step": "awaiting_quota_id"}})
    await safe_edit_text(cb, "⚙️ **تغییر سهمیه کاربر:**\n\nلطفاً آیدی عددی کاربر را بفرستید:", reply_markup=back_to_menu_kb(True))
    await cb.answer()

@router.message(F.from_user.id == ADMIN_ID, is_admin_active)
async def admin_message_handler(message: Message, bot: Bot):
    s = storage.get_session(message.from_user.id)
    admin_state = s.get("admin", {})
    step = admin_state.get("step")

    if step == "awaiting_broadcast":
        storage.update_session(message.from_user.id, {"admin": {}})
        await message.answer("⏳ در حال ارسال پیام همگانی به تمام کاربران...")
        users = list(storage.USERS.keys())
        total_users = len(users)
        success_count = 0
        failed_count = 0

        for uid_str in users:
            try:
                await bot.copy_message(
                    chat_id=int(uid_str),
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
                success_count += 1
            except Exception:
                failed_count += 1

        report = (
            "✅ **پیام همگانی با موفقیت ارسال شد!**\n\n"
            f"👥 **کل کاربران ثبت‌شده:** `{total_users}` نفر\n"
            f"✅ **ارسال موفق:** `{success_count}` نفر\n"
            f"❌ **ناموفق (بلاک یا حذف حساب):** `{failed_count}` نفر"
        )
        await message.answer(report, reply_markup=admin_panel_kb())

    elif step == "awaiting_dm_id":
        target_id = message.text.strip()
        if target_id.isdigit():
            storage.update_session(message.from_user.id, {"admin": {"step": "awaiting_dm_text", "target_id": int(target_id)}})
            await message.answer(f"حالا پیام مورد نظر برای کاربر `{target_id}` را بفرستید (متن، عکس، ویدیو و ...):")
        else:
            await message.answer("آیدی باید فقط شامل عدد باشد.")

    elif step == "awaiting_dm_text":
        target_id = admin_state.get("target_id")
        storage.update_session(message.from_user.id, {"admin": {}})
        try:
            await bot.copy_message(
                chat_id=target_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            await message.answer(f"✅ پیام با موفقیت به کاربر `{target_id}` ارسال شد.", reply_markup=admin_panel_kb())
        except Exception as e:
            await message.answer(f"❌ خطا در ارسال پیام به کاربر: {e}", reply_markup=admin_panel_kb())

    elif step == "awaiting_quota_id":
        target_id = message.text.strip()
        if target_id.isdigit():
            storage.update_session(message.from_user.id, {"admin": {"step": "awaiting_quota_val", "target_id": int(target_id)}})
            await message.answer(f"سهمیه روزانه جدید برای کاربر `{target_id}` را وارد کنید (مثال: 10 یا 100):")
        else:
            await message.answer("آیدی باید فقط شامل عدد باشد.")

    elif step == "awaiting_quota_val":
        target_id = admin_state.get("target_id")
        val_str = message.text.strip()
        if val_str.isdigit():
            u = storage.get_user(target_id)
            u["daily_limit"] = int(val_str)
            storage.save()
            storage.update_session(message.from_user.id, {"admin": {}})
            await message.answer(f"✅ سهمیه روزانه کاربر `{target_id}` به `{val_str}` تغییر یافت.", reply_markup=admin_panel_kb())
        else:
            await message.answer("مقدار سهمیه باید عدد باشد.")
