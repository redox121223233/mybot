import logging
import traceback
from aiogram import Bot, Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputSticker
from aiogram.exceptions import TelegramBadRequest

from ..config import ADMIN_ID, FORBIDDEN_WORDS
from ..services.storage import storage
from ..utils.image_processing import render_image
from ..utils.video_processing import is_ffmpeg_installed, process_video_to_webm
from ..utils.helpers import _quota_left, is_valid_pack_name
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
            s.update({
                "current_pack_short_name": pack_short_name,
                "current_pack_title": pack["name"],
                "pack_wizard": {},
                "mode": mode
            })
            if mode == "simple":
                s["simple"] = {}
                await safe_edit_text(cb, f"پک «{pack['name']}» انتخاب شد. متن را بفرستید.")
            else:
                s["ai"] = {}
                await safe_edit_text(cb, f"پک «{pack['name']}» انتخاب شد. نوع استیکر؟", reply_markup=ai_type_kb())
    elif action == "new" or action == "start_creation":
        mode = parts[2] if action == "new" and len(parts) > 2 else s.get("pack_wizard", {}).get("mode", "simple")
        s["pack_wizard"] = {"step": "awaiting_name", "mode": mode}
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
            await safe_edit_text(cb, "عکس پس‌زمینه را ارسال کنید.")
        else:
            img = render_image(simple_data["text"], "center", "center", "Default", "#FFFFFF", "medium", bg_mode=bg_mode)
            await cb.message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("simple"))
    elif action == "confirm":
        img = render_image(simple_data["text"], "center", "center", "Default", "#FFFFFF", "medium",
                          bg_mode=simple_data.get("bg_mode", "transparent"),
                          bg_photo=simple_data.get("bg_photo_bytes"), as_webp=True)
        s["last_sticker"] = img
        s["last_sticker_format"] = "static"
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
            s["mode"] = "ai_awaiting_source"
            await safe_edit_text(cb, "منبع استیکر؟", reply_markup=ai_image_source_kb())
        else:
            s["mode"] = "ai_awaiting_video"
            await safe_edit_text(cb, "حالا ویدیوی خود را ارسال کنید (حداکثر ۳ ثانیه).")
    elif action == "source":
        if parts[2] == "text":
            s["mode"] = "ai_awaiting_text_for_image"
            await safe_edit_text(cb, "متن استیکر را بفرست:")
        else:
            ai_data["awaiting_bg_photo"] = True
            s["mode"] = "ai_awaiting_source"
            await safe_edit_text(cb, "عکس را ارسال کنید:")
    elif action == "vpos":
        ai_data["v_pos"] = parts[2]
        await safe_edit_text(cb, "موقعیت افقی؟", reply_markup=ai_hpos_kb())
    elif action == "hpos":
        ai_data["h_pos"] = parts[2]
        await safe_edit_text(cb, "رنگ متن؟", reply_markup=ai_color_kb())
    elif action == "color":
        ai_data["color"] = parts[2]
        await safe_edit_text(cb, "اندازه فونت؟", reply_markup=ai_size_kb())
    elif action in ["size", "edit"]:
        if action == "size": ai_data["size"] = parts[2]
        img = render_image(ai_data.get("text","Sample"), ai_data.get("v_pos", "center"), ai_data.get("h_pos", "center"),
                          "Default", ai_data.get("color", "#FFFFFF"), ai_data.get("size", "medium"),
                          bg_photo=ai_data.get("bg_photo_bytes"))
        await cb.message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("ai"))
    elif action == "confirm":
        if _quota_left(storage.get_user(uid), uid == ADMIN_ID) <= 0:
            await cb.answer("سهمیه تمام شد!", show_alert=True); return

        sticker_type = ai_data.get("type", "image")
        if sticker_type == "video":
            await safe_edit_text(cb, "در حال پردازش ویدیو...")
            video_bytes = ai_data.get("video_bytes")
            if video_bytes:
                text_overlay = {k: ai_data.get(k) for k in ["text", "v_pos", "h_pos", "color", "size"]}
                text_overlay["font_key"] = "Default"
                text_overlay["color_hex"] = text_overlay.pop("color", "#FFFFFF")
                text_overlay["size_key"] = text_overlay.pop("size", "medium")

                webm_bytes = await process_video_to_webm(video_bytes, text_overlay)
                if webm_bytes:
                    s["last_sticker"] = webm_bytes
                    s["last_sticker_format"] = "video"
                    storage.get_user(uid)["ai_used"] += 1
                    await cb.message.answer_sticker(BufferedInputFile(webm_bytes, "s.webm"))
                    await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
                else:
                    await cb.message.answer("خطا در پردازش ویدیو.", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
        else:
            img = render_image(ai_data["text"], ai_data["v_pos"], ai_data["h_pos"], "Default", ai_data["color"], ai_data["size"],
                              bg_photo=ai_data.get("bg_photo_bytes"), as_webp=True)
            s["last_sticker"] = img
            s["last_sticker_format"] = "static"
            storage.get_user(uid)["ai_used"] += 1
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
                # Re-render as PNG for static sticker sets
                if s.get("mode") == "simple":
                    d = s.get("simple", {})
                    png = render_image(d.get("text"), "center", "center", "Default", "#FFFFFF", "medium", bg_mode=d.get("bg_mode"), bg_photo=d.get("bg_photo_bytes"), as_webp=False)
                else:
                    d = s.get("ai", {})
                    png = render_image(d.get("text"), d.get("v_pos"), d.get("h_pos"), "Default", d.get("color"), d.get("size"), bg_photo=d.get("bg_photo_bytes"), as_webp=False)
                sticker = InputSticker(sticker=BufferedInputFile(png, "s.png"), format="static", emoji_list=["😀"])

            await bot.add_sticker_to_set(user_id=uid, name=pack_name, sticker=sticker)

            # Reset state but preserve pack info
            mode = s.get("mode", "simple")
            storage.reset_session(uid)
            s = storage.get_session(uid)
            s.update({"current_pack_short_name": pack_name, "current_pack_title": pack_title, "mode": mode})

            await cb.message.answer(f"✅ استیکر به پک «{pack_title}» اضافه شد!\nhttps://t.me/addstickers/{pack_name}\n\nبرای استیکر بعدی، متن جدید بفرستید.",
                                   reply_markup=back_to_menu_kb(uid == ADMIN_ID))
        except Exception as e:
            logger.error(f"Error adding sticker: {e}")
            await cb.message.answer(f"خطا در افزودن به پک: {e}", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    elif action == "no":
        s["await_feedback"] = True
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
            s.update({"current_pack_short_name": short_name, "current_pack_title": pack_name, "pack_wizard": {}, "mode": mode})
            if mode == "simple":
                await message.answer(f"پک ساخته شد! حالا متن استیکر را بفرستید.")
            else:
                await message.answer(f"پک ساخته شد! حالا نوع استیکر را انتخاب کنید:", reply_markup=ai_type_kb())
        except Exception as e:
            await message.answer(f"خطا: {e}")
        return

    if message.photo:
        s_simple, s_ai = s.get("simple", {}), s.get("ai", {})
        if s.get("mode") == "simple" and s_simple.get("awaiting_bg_photo"):
            file = await bot.download(message.photo[-1].file_id)
            s_simple["bg_photo_bytes"] = file.read()
            s_simple["awaiting_bg_photo"] = False
            img = render_image(s_simple["text"], "center", "center", "Default", "#FFFFFF", "medium", bg_photo=s_simple["bg_photo_bytes"])
            await message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("simple"))
        elif s.get("mode") == "ai_awaiting_source" and s_ai.get("awaiting_bg_photo"):
            file = await bot.download(message.photo[-1].file_id)
            s_ai["bg_photo_bytes"] = file.read()
            s_ai["awaiting_bg_photo"] = False
            s["mode"] = "ai_awaiting_text_for_image"
            await message.answer("عکس دریافت شد. حالا متن را بفرستید:")
        return

    if message.video or message.animation:
        video = message.video or message.animation
        if s.get("mode") == "ai_awaiting_video":
            if not await is_ffmpeg_installed():
                await message.answer("پردازش ویدیو در حال حاضر فعال نیست.")
                return
            file = await bot.download(video.file_id)
            s.get("ai", {})["video_bytes"] = file.read()
            s["mode"] = "ai_awaiting_text_for_video"
            await message.answer("ویدیو دریافت شد. حالا متن را بفرستید.")
        return

    if message.text:
        if s.get("await_feedback"):
            s["await_feedback"] = False
            await message.answer("ممنون از بازخوردت!", reply_markup=back_to_menu_kb(is_admin))
            return

        if s.get("mode") in ["ai_awaiting_text_for_video", "ai_awaiting_text_for_image"]:
            s["ai"]["text"] = message.text.strip()
            s["mode"] = "ai"
            await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
            return

        if s.get("current_pack_short_name"):
            mode = s.get("mode", "simple")
            if mode == "simple":
                s["simple"]["text"] = message.text.strip()
                await message.answer("پس‌زمینه را انتخاب کنید:", reply_markup=simple_bg_kb())
            elif mode == "ai":
                s["ai"]["text"] = message.text.strip()
                await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
            return

    await message.answer("دستور مشخص نیست.", reply_markup=main_menu_kb(is_admin))
