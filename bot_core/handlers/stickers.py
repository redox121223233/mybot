import logging
import traceback
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputSticker
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from ..config import ADMIN_ID, FORBIDDEN_WORDS, SUPPORT_USERNAME
from ..services.storage import storage
from ..utils.image_processing import render_image
from ..utils.video_processing import is_ffmpeg_installed
from ..utils.helpers import _quota_left, is_valid_pack_name
from ..bot_logic import convert_video_to_sticker, convert_gif_to_sticker
from ..keyboards import (
    simple_bg_kb, after_preview_kb, rate_kb, ai_type_kb,
    ai_image_source_kb, ai_vpos_kb, ai_hpos_kb, ai_color_kb, ai_size_kb,
    back_to_menu_kb, main_menu_kb
)
from .common import require_channel_membership, safe_edit_text

logger = logging.getLogger(__name__)
router = Router()

# --- Pack Handlers ---
@router.callback_query(F.data.startswith("pack:"))
async def on_pack_actions(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    parts = cb.data.split(":")
    uid = cb.from_user.id
    s = storage.get_session(uid)
    action = parts[1]

    if action == "select":
        pack_short_name = parts[2]
        mode = parts[3] if len(parts) > 3 else "simple"
        packs = storage.get_user_packs(uid)
        pack = next((p for p in packs if p["short_name"] == pack_short_name), None)
        if pack:
            storage.set_current_pack(uid, pack_short_name)
            storage.update_session(uid, {
                "current_pack_short_name": pack_short_name,
                "current_pack_title": pack["name"],
                "pack_wizard": {},
                "mode": mode
            })
            if mode == "simple":
                storage.update_session(uid, {"simple": {}})
                await safe_edit_text(cb, f"پک «{pack['name']}» انتخاب شد. متن را بفرستید.")
            else:
                storage.update_session(uid, {"ai": {}})
                await safe_edit_text(cb, f"پک «{pack['name']}» انتخاب شد. نوع استیکر؟", reply_markup=ai_type_kb())
    elif action == "new" or action == "start_creation":
        mode = parts[2] if action == "new" and len(parts) > 2 else s.get("pack_wizard", {}).get("mode", "simple")
        storage.update_session(uid, {"pack_wizard": {"step": "awaiting_name", "mode": mode}})
        rules_text = (
            "نام پک را بنویس (مثال: my_stickers):\n\n"
            "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
            "• باید با حرف شروع شود\n"
            "• حداکثر ۵۰ کاراکتر"
        )
        await safe_edit_text(cb, rules_text)
    await cb.answer()

# --- Simple Sticker Handlers ---
@router.callback_query(F.data.startswith("simple:"))
async def on_simple_actions(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    action = cb.data.split(":")[1]
    uid = cb.from_user.id
    s = storage.get_session(uid)
    simple_data = s.get("simple", {})

    if action == "bg":
        bg_mode = cb.data.split(":")[-1]
        simple_data["bg_mode"] = bg_mode
        if bg_mode == "photo_prompt":
            simple_data["awaiting_bg_photo"] = True
            storage.update_session(uid, {"simple": simple_data})
            await safe_edit_text(cb, "عکس پس‌زمینه را ارسال کنید.")
        else:
            storage.update_session(uid, {"simple": simple_data})
            img = render_image(simple_data["text"], "center", "center", "Default", "#FFFFFF", "medium", bg_mode=bg_mode)
            await cb.message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("simple"))
    elif action == "confirm":
        img = render_image(simple_data["text"], "center", "center", "Default", "#FFFFFF", "medium",
                          bg_mode=simple_data.get("bg_mode", "transparent"),
                          bg_photo=simple_data.get("bg_photo_bytes"), as_webp=True)
        storage.update_session(uid, {"last_sticker": img, "last_sticker_format": "static"})
        await cb.message.answer_sticker(BufferedInputFile(img, "s.webp"))
        await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
    elif action == "edit":
        await safe_edit_text(cb, "پس‌زمینه رو انتخاب کن:", reply_markup=simple_bg_kb())
    await cb.answer()

# --- AI Sticker Handlers ---
@router.callback_query(F.data.startswith("ai:"))
async def on_ai_actions(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    parts = cb.data.split(":")
    uid = cb.from_user.id
    s = storage.get_session(uid)
    action = parts[1]
    ai_data = s.get("ai", {})

    if action == "type":
        ai_data["type"] = parts[2]
        if parts[2] == "image":
            storage.update_session(uid, {"ai": ai_data, "mode": "ai_awaiting_source"})
            await safe_edit_text(cb, "منبع استیکر؟", reply_markup=ai_image_source_kb())
        else:
            storage.update_session(uid, {"ai": ai_data, "mode": "ai_awaiting_video"})
            await safe_edit_text(cb, "حالا ویدیو یا گیف خود را ارسال کنید (حداکثر ۳ ثانیه).")
    elif action == "source":
        if parts[2] == "text":
            storage.update_session(uid, {"mode": "ai_awaiting_text_for_image"})
            await safe_edit_text(cb, "متن استیکر را بفرست:")
        else:
            ai_data["awaiting_bg_photo"] = True
            storage.update_session(uid, {"ai": ai_data, "mode": "ai_awaiting_source"})
            await safe_edit_text(cb, "عکس را ارسال کنید:")
    elif action == "vpos":
        ai_data["v_pos"] = parts[2]
        storage.update_session(uid, {"ai": ai_data})
        await safe_edit_text(cb, "موقعیت افقی؟", reply_markup=ai_hpos_kb())
    elif action == "hpos":
        ai_data["h_pos"] = parts[2]
        storage.update_session(uid, {"ai": ai_data})
        await safe_edit_text(cb, "رنگ متن؟", reply_markup=ai_color_kb())
    elif action == "color":
        ai_data["color"] = parts[2]
        storage.update_session(uid, {"ai": ai_data})
        await safe_edit_text(cb, "اندازه فونت؟", reply_markup=ai_size_kb())
    elif action in ["size", "edit"]:
        if action == "size":
            ai_data["size"] = parts[2]
            storage.update_session(uid, {"ai": ai_data})

        if ai_data.get("type") == "video" and not ai_data.get("text"):
            kb = InlineKeyboardBuilder()
            kb.button(text="تایید بدون متن", callback_data="ai:confirm")
            kb.button(text="افزودن متن", callback_data="ai:source:text")
            kb.button(text="بازگشت", callback_data="menu:home")
            await cb.message.answer("آیا می‌خواهید متنی روی ویدیو باشد یا بدون متن ادامه می‌دهید؟", reply_markup=kb.as_markup())
        else:
            img = render_image(ai_data.get("text","Sample"), ai_data.get("v_pos", "center"), ai_data.get("h_pos", "center"),
                              "Default", ai_data.get("color", "#FFFFFF"), ai_data.get("size", "medium"),
                              bg_photo=ai_data.get("bg_photo_bytes"))
            await cb.message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("ai"))
    elif action == "confirm":
        if _quota_left(storage.get_user(uid), uid == ADMIN_ID) <= 0:
            await cb.answer("سهمیه تمام شد!", show_alert=True); return

        sticker_type = ai_data.get("type", "video" if ai_data.get("video_bytes") else "image")
        if sticker_type == "video":
            await safe_edit_text(cb, "در حال پردازش ویدیو/گیف...")
            video_bytes = ai_data.get("video_bytes")
            if video_bytes:
                text_overlay = {k: ai_data.get(k) for k in ["text", "v_pos", "h_pos", "color", "size"]}
                text_overlay["font_key"] = "Default"
                text_overlay["color_hex"] = text_overlay.pop("color", "#FFFFFF")
                text_overlay["size_key"] = text_overlay.pop("size", "medium")

                if not text_overlay.get("text"):
                    text_overlay = None

                # Use the new utility hub functions
                webm_bytes = await convert_video_to_sticker(video_bytes, text_overlay)
                if webm_bytes:
                    storage.update_session(uid, {"last_sticker": webm_bytes, "last_sticker_format": "video"})
                    storage.get_user(uid)["ai_used"] += 1
                    storage.save()
                    await cb.message.answer_sticker(BufferedInputFile(webm_bytes, "s.webm"))
                    await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
                else:
                    await cb.message.answer("خطا در پردازش ویدیو. مطمئن شوید زمان آن کمتر از ۳ ثانیه است.", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
        else:
            img = render_image(ai_data["text"], ai_data["v_pos"], ai_data.get("h_pos", "center"), "Default", ai_data["color"], ai_data["size"],
                              bg_photo=ai_data.get("bg_photo_bytes"), as_webp=True)
            storage.update_session(uid, {"last_sticker": img, "last_sticker_format": "static"})
            storage.get_user(uid)["ai_used"] += 1
            storage.save()
            await cb.message.answer_sticker(BufferedInputFile(img, "s.webp"))
            await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
    await cb.answer()

# --- Sticker Rating and Final Addition ---
@router.callback_query(F.data.startswith("rate:"))
async def on_rate_actions(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    action = cb.data.split(":")[1]
    uid = cb.from_user.id
    s = storage.get_session(uid)

    if action == "yes":
        sticker_bytes = s.get("last_sticker")
        pack_name = s.get("current_pack_short_name")
        pack_title = s.get("current_pack_title")

        if not all([sticker_bytes, pack_name, pack_title]):
            await safe_edit_text(cb, "خطا: اطلاعات پک یافت نشد.", reply_markup=back_to_menu_kb(uid == ADMIN_ID)); return

        await safe_edit_text(cb, "در حال افزودن به پک...")
        try:
            format = s.get("last_sticker_format", "static")
            if format == "video":
                sticker = InputSticker(sticker=BufferedInputFile(sticker_bytes, "s.webm"), format="video", emoji_list=["😀"])
            else:
                if s.get("mode") == "simple":
                    d = s.get("simple", {})
                    png = render_image(d.get("text"), "center", "center", "Default", "#FFFFFF", "medium", bg_mode=d.get("bg_mode"), bg_photo=d.get("bg_photo_bytes"), as_webp=False)
                else:
                    d = s.get("ai", {})
                    png = render_image(d.get("text"), d.get("v_pos"), d.get("h_pos"), "Default", d.get("color"), d.get("size"), bg_photo=d.get("bg_photo_bytes"), as_webp=False)
                sticker = InputSticker(sticker=BufferedInputFile(png, "s.png"), format="static", emoji_list=["😀"])

            await bot.add_sticker_to_set(user_id=uid, name=pack_name, sticker=sticker)

            mode = s.get("mode", "simple")
            storage.reset_session(uid)
            storage.update_session(uid, {"current_pack_short_name": pack_name, "current_pack_title": pack_title, "mode": mode})

            success_msg = (
                f"✅ استیکر با موفقیت به پک «{pack_title}» اضافه شد!\n"
                f"https://t.me/addstickers/{pack_name}\n\n"
                "ℹ️ **نکته مهم:** ممکن است چند دقیقه طول بکشد تا تلگرام کش خود را بروزرسانی کند و استیکر جدید در لیست شما ظاهر شود.\n"
                "اگر استیکر را نمی‌بینید، یکبار پک را حذف و مجدداً از لینک بالا اضافه کنید.\n\n"
                f"🆘 اگر مشکلی داشتید به پشتیبانی پیام بدید: {SUPPORT_USERNAME}\n\n"
                "برای استیکر بعدی، متن یا فایل جدید بفرستید."
            )
            await cb.message.answer(success_msg, reply_markup=back_to_menu_kb(uid == ADMIN_ID))
        except Exception as e:
            logger.error(f"Error adding sticker: {e}")
            await cb.message.answer(f"خطا در افزودن به پک: {e}\n\nاگر این مشکل تکرار شد به پشتیبانی پیام بدید.", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    elif action == "no":
        storage.update_session(uid, {"await_feedback": True})
        await safe_edit_text(cb, "چه چیزی رو دوست نداشتی؟")
    await cb.answer()

# --- Generic Message Handler ---
@router.message()
async def on_message(message: Message, bot: Bot):
    if not await require_channel_membership(message, bot): return
    uid = message.from_user.id
    s = storage.get_session(uid)
    is_admin = (uid == ADMIN_ID)

    if s.get("pack_wizard", {}).get("step") == "awaiting_name" and message.text:
        pack_name = message.text.strip().lower()
        from ..utils.helpers import is_valid_pack_name
        if any(word in pack_name for word in FORBIDDEN_WORDS) or not is_valid_pack_name(pack_name):
            await message.answer("نام نامعتبر است."); return

        bot_info = await bot.get_me()
        short_name = f"{pack_name}_by_{bot_info.username}"
        await message.answer("در حال ساخت پک...")
        try:
            dummy = render_image("First", "center", "center", "Default", "#FFFFFF", "medium", as_webp=False)
            sticker = InputSticker(sticker=BufferedInputFile(dummy, "s.png"), format="static", emoji_list=["🎉"])
            await bot.create_new_sticker_set(uid, short_name, pack_name, stickers=[sticker], sticker_format='static')
            storage.add_user_pack(uid, pack_name, short_name)
            mode = s["pack_wizard"].get("mode", "simple")
            storage.update_session(uid, {"current_pack_short_name": short_name, "current_pack_title": pack_name, "pack_wizard": {}, "mode": mode})
            if mode == "simple":
                await message.answer(f"پک ساخته شد! حالا متن استیکر را بفرستید.")
            else:
                await message.answer(f"پک ساخته شد! حالا نوع استیکر را انتخاب کنید:", reply_markup=ai_type_kb())
        except Exception as e:
            await message.answer(f"خطا در ساخت پک: {e}")
        return

    if message.photo:
        s_simple, s_ai = s.get("simple", {}), s.get("ai", {})
        if s.get("mode") == "simple" and s_simple.get("awaiting_bg_photo"):
            file = await bot.download(message.photo[-1].file_id)
            s_simple["bg_photo_bytes"] = file.read()
            s_simple["awaiting_bg_photo"] = False
            storage.update_session(uid, {"simple": s_simple})
            img = render_image(s_simple["text"], "center", "center", "Default", "#FFFFFF", "medium", bg_photo=s_simple["bg_photo_bytes"])
            await message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("simple"))
            return
        elif s.get("mode") == "ai_awaiting_source" and s_ai.get("awaiting_bg_photo"):
            file = await bot.download(message.photo[-1].file_id)
            s_ai["bg_photo_bytes"] = file.read()
            s_ai["awaiting_bg_photo"] = False
            storage.update_session(uid, {"ai": s_ai, "mode": "ai_awaiting_text_for_image"})
            await message.answer("عکس دریافت شد. حالا متن را بفرستید:")
            return

    # Handle Video, GIF, and Animation proactively
    if message.video or message.animation:
        video = message.video or message.animation
        if not await is_ffmpeg_installed():
            await message.answer("پردازش ویدیو در حال حاضر فعال نیست.")
            return

        # If no pack active, prompt to select/create
        if not s.get("current_pack_short_name"):
            await message.answer("ابتدا باید یک پک استیکر بسازید یا انتخاب کنید.", reply_markup=main_menu_kb(is_admin))
            return

        await message.answer("در حال دریافت فایل...")
        file = await bot.download(video.file_id)
        file_bytes = file.read()

        ai_data = s.get("ai", {})
        ai_data.update({"video_bytes": file_bytes, "type": "video"})
        storage.update_session(uid, {"ai": ai_data, "mode": "ai_confirm_video_text"})

        kb = InlineKeyboardBuilder()
        kb.button(text="بدون متن", callback_data="ai:confirm")
        kb.button(text="افزودن متن", callback_data="ai:source:text")
        await message.answer("فایل دریافت شد. آیا می‌خواهید متنی روی آن اضافه کنید؟", reply_markup=kb.as_markup())
        return

    if message.text:
        if s.get("await_feedback"):
            storage.update_session(uid, {"await_feedback": False})
            await message.answer("ممنون از بازخوردت!", reply_markup=back_to_menu_kb(is_admin))
            return

        if s.get("mode") in ["ai_awaiting_text_for_video", "ai_awaiting_text_for_image"]:
            ai_data = s.get("ai", {})
            ai_data["text"] = message.text.strip()
            storage.update_session(uid, {"ai": ai_data, "mode": "ai"})
            await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
            return

        if s.get("current_pack_short_name"):
            mode = s.get("mode", "simple")
            if mode == "simple":
                storage.update_session(uid, {"simple": {"text": message.text.strip()}})
                await message.answer("پس‌زمینه را انتخاب کنید:", reply_markup=simple_bg_kb())
            elif mode == "ai":
                ai_data = s.get("ai", {})
                ai_data["text"] = message.text.strip()
                storage.update_session(uid, {"ai": ai_data})
                await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
            return

    await message.answer("دستور مشخص نیست.", reply_markup=main_menu_kb(is_admin))
