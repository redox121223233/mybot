# Vercel-compatible bot handlers
"""
Bot handlers for all message and callback interactions
"""
from aiogram import Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
import asyncio
from html import escape  # Import the escape function

from .bot_logic import (
    router, USERS, SESSIONS, ADMIN_PENDING, BOT_USERNAME,
    user, sess, reset_mode, get_user_packs, add_user_pack, set_current_pack, get_current_pack,
    render_image, check_channel_membership, require_channel_membership,
    main_menu_kb, back_to_menu_kb, simple_bg_kb, after_preview_kb, rate_kb,
    pack_selection_kb, add_to_pack_kb, ai_type_kb, ai_image_source_kb,
    ai_vpos_kb, ai_hpos_kb, admin_panel_kb,
    check_pack_exists, is_valid_pack_name, process_video_to_webm,
    is_ffmpeg_installed, ADMIN_ID, FORBIDDEN_WORDS, DEFAULT_PALETTE, NAME_TO_HEX, POS_WORDS, SIZE_WORDS,
    _quota_left, _fmt_eta, _today_start_ts
)
from aiogram.types import BufferedInputFile, InputSticker
import pydantic_core
import traceback

@router.callback_query(F.data == "check_membership")
async def on_check_membership(cb: CallbackQuery, bot: Bot):
    from .bot_logic import check_channel_membership
    is_member = await check_channel_membership(bot, cb.from_user.id)
    if is_member:
        await cb.message.answer(
            "عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.",
            reply_markup=main_menu_kb(cb.from_user.id == ADMIN_ID)
        )
    else:
        await cb.answer("شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
    await cb.answer()

@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    reset_mode(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    await cb.message.answer(
        "منوی اصلی:",
        reply_markup=main_menu_kb(is_admin)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:admin")
async def on_admin_panel(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("شما دسترسی به این بخش را ندارید.", show_alert=True)
        return
    await cb.message.answer("پنل ادمین:", reply_markup=admin_panel_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:broadcast")
async def on_admin_broadcast(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "broadcast"
    await cb.message.answer("پیام همگانی خود را ارسال کنید. برای انصراف /cancel را بفرستید.")
    await cb.answer()

@router.callback_query(F.data == "admin:dm_prompt")
async def on_admin_dm_prompt(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "dm_get_user"
    await cb.message.answer("آیدی عددی کاربر مورد نظر را ارسال کنید. برای انصراف /cancel را بفرستید.")
    await cb.answer()

@router.callback_query(F.data == "admin:quota_prompt")
async def on_admin_quota_prompt(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "quota_get_user"
    await cb.message.answer("آیدی عددی کاربر مورد نظر را برای تغییر سهمیه ارسال کنید. برای انصراف /cancel را بفرستید.")
    await cb.answer()

@router.callback_query(F.data == "menu:help")
async def on_help(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    help_text = (
        "راهنما\n\n"
        "• استیکر ساده: ساخت استیکر با تنظیمات سریع\n"
        "• استیکر ساز پیشرفته: ساخت استیکر با تنظیمات پیشرفته\n"
        "• سهمیه امروز: محدودیت استفاده روزانه\n"
        "• پشتیبانی: ارتباط با ادمین"
    )
    await cb.message.answer(help_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:support")
async def on_support(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    from .bot_logic import SUPPORT_USERNAME
    await cb.message.answer(
        f"پشتیبانی: {SUPPORT_USERNAME}",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:quota")
async def on_quota(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    quota_txt = "نامحدود" if is_admin else f"{left} از {u.get('daily_limit', 5)}"
    await cb.message.answer(
        f"سهمیه امروز: {quota_txt}",
        reply_markup=back_to_menu_kb(is_admin)
    )
    await cb.answer()

@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    uid = cb.from_user.id
    
    user_packs = get_user_packs(uid)
    if user_packs:
        s["pack_wizard"] = {"mode": "simple"}
        await cb.message.answer(
            "می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟",
            reply_markup=pack_selection_kb(uid, "simple")
        )
    else:
        s["pack_wizard"] = {"step": "awaiting_name", "mode": "simple"}
        rules_text = (
            "نام پک را بنویس (مثال: my_stickers):\n\n"
            "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
            "• باید با حرف شروع شود\n"
            "• نباید با زیرخط تمام شود\n"
            "• نباید دو زیرخط پشت سر هم داشته باشد\n"
            "• حداکثر ۵۰ کاراکتر (به دلیل افزودن نام ربات)"
        )
        await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:ai")
async def on_ai(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)

    if left <= 0 and not is_admin:
        await cb.message.answer(
            "سهمیه امروز تمام شد!",
            reply_markup=back_to_menu_kb(is_admin)
        )
        await cb.answer()
        return

    s = sess(cb.from_user.id)
    uid = cb.from_user.id
    
    user_packs = get_user_packs(uid)
    if user_packs:
        s["pack_wizard"] = {"mode": "ai"}
        await cb.message.answer(
            "می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟",
            reply_markup=pack_selection_kb(uid, "ai")
        )
    else:
        s["pack_wizard"] = {"step": "awaiting_name", "mode": "ai"}
        rules_text = (
            "نام پک را بنویس (مثال: my_stickers):\n\n"
            "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
            "• باید با حرف شروع شود\n"
            "• نباید با زیرخط تمام شود\n"
            "• نباید دو زیرخط پشت سر هم داشته باشد\n"
            "• حداکثر ۵۰ کاراکتر (به دلیل افزودن نام ربات)"
        )
        await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("pack:select:"))
async def on_pack_select(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    pack_short_name = cb.data.split(":")[-1]
    uid = cb.from_user.id
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
            await cb.message.answer(
                f"پک «{selected_pack['name']}» انتخاب شد.\n\nمتن استیکر ساده رو بفرست:",
                reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
            )
        elif mode == "ai":
            s["mode"] = "ai"
            s["ai"] = {
                "text": None, "v_pos": "center", "h_pos": "center", "font": "Default",
                "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None
            }
            await cb.message.answer(
                f"پک «{selected_pack['name']}» انتخاب شد.\n\nنوع استیکر پیشرفته را انتخاب کنید:",
                reply_markup=ai_type_kb()
            )
    
    await cb.answer()

@router.callback_query(F.data.startswith("pack:new:"))
async def on_pack_new(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    mode = cb.data.split(":")[-1]
    s = sess(cb.from_user.id)
    s["pack_wizard"] = {"step": "awaiting_name", "mode": mode}
    rules_text = (
        "برای ایجاد پک جدید، یک نام انگلیسی ارسال کنید.\n\n"
        "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
        "• حداکثر ۵۰ کاراکتر"
    )
    await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("simple:bg:"))
async def on_simple_bg(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)["simple"]
    mode = cb.data.split(":")[-1]
    if mode == "photo_prompt":
        s["awaiting_bg_photo"] = True
        await cb.message.answer("عکس مورد نظر برای پس‌زمینه را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    else:
        s["bg_mode"] = mode
        s["bg_photo_bytes"] = None
        if s.get("text"):
            img = render_image(
                text=s["text"],
                v_pos="center", h_pos="center",
                font_key="Default",
                color_hex="#FFFFFF",
                size_key="medium",
                bg_mode=mode,
                bg_photo=s.get("bg_photo_bytes"),
                as_webp=False
            )
            file_obj = BufferedInputFile(img, filename="preview.png")
            await cb.message.answer_photo(
                file_obj,
                caption="پیش‌نمایش آماده است",
                reply_markup=after_preview_kb("simple")
            )
    await cb.answer()

@router.callback_query(F.data == "simple:confirm")
async def on_simple_confirm(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    simple_data = s["simple"]
    img = render_image(
        text=simple_data["text"] or "سلام",
        v_pos="center", h_pos="center",
        font_key="Default",
        color_hex="#FFFFFF",
        size_key="medium",
        bg_mode=simple_data.get("bg_mode") or "transparent",
        bg_photo=simple_data.get("bg_photo_bytes"),
        as_webp=True
    )
    s["last_sticker"] = img
    await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
    await cb.message.answer(
        "از این استیکر راضی بودی؟",
        reply_markup=rate_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "simple:edit")
async def on_simple_edit(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    await cb.message.answer(
        "پس‌زمینه رو انتخاب کن:",
        reply_markup=simple_bg_kb()
    )
    await cb.answer()

@router.callback_query(F.data.startswith("ai:type:"))
async def on_ai_type(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    sticker_type = cb.data.split(":")[-1]
    s = sess(cb.from_user.id)
    s["ai"]["sticker_type"] = sticker_type

    if sticker_type == "image":
        await cb.message.answer("منبع استیکر تصویری را انتخاب کنید:", reply_markup=ai_image_source_kb())
    elif sticker_type == "video":
        if not is_ffmpeg_installed():
            await cb.message.answer(
                "قابلیت ویدیو فعال نیست.",
                reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
            )
        else:
            await cb.message.answer("یک فایل ویدیو ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "ai:source:text")
async def on_ai_source_text(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    await cb.message.answer("متن استیکر را بفرست:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "ai:source:photo")
async def on_ai_source_photo(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    sess(cb.from_user.id)["ai"]["awaiting_bg_photo"] = True
    await cb.message.answer("عکس را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("ai:vpos:"))
async def on_ai_vpos(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    v_pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["v_pos"] = v_pos
    await cb.message.answer("موقعیت افقی متن:", reply_markup=ai_hpos_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ai:hpos:"))
async def on_ai_hpos(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    h_pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["h_pos"] = h_pos

    kb = InlineKeyboardBuilder()
    for name, hx in DEFAULT_PALETTE:
        kb.button(text=name, callback_data=f"ai:color:{hx}")
    kb.adjust(4)

    await cb.message.answer("رنگ متن:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:color:")))
async def on_ai_color(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    color = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["color"] = color

    kb = InlineKeyboardBuilder()
    for label, val in [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]:
        kb.button(text=label, callback_data=f"ai:size:{val}")
    kb.adjust(3)

    await cb.message.answer("اندازه فونت:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:size:")))
async def on_ai_size(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    size = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["size"] = size

    ai_data = sess(cb.from_user.id)["ai"]
    img = render_image(
        text=ai_data.get("text") or "متن ساده",
        v_pos=ai_data["v_pos"],
        h_pos=ai_data["h_pos"],
        font_key="Default",
        color_hex=ai_data["color"],
        size_key=size,
        bg_mode="transparent",
        bg_photo=ai_data.get("bg_photo_bytes"),
        as_webp=False
    )

    file_obj = BufferedInputFile(img, filename="preview.png")
    await cb.message.answer_photo(
        file_obj,
        caption="پیش‌نمایش آماده است",
        reply_markup=after_preview_kb("ai")
    )
    await cb.answer()

@router.callback_query(F.data == "ai:confirm")
async def on_ai_confirm(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)

    if left <= 0 and not is_admin:
        await cb.answer("سهمیه تمام شد!", show_alert=True)
        return

    ai_data = sess(cb.from_user.id)["ai"]
    img = render_image(
        text=ai_data.get("text") or "سلام",
        v_pos=ai_data["v_pos"],
        h_pos=ai_data["h_pos"],
        font_key="Default",
        color_hex=ai_data["color"],
        size_key=ai_data["size"],
        bg_mode="transparent",
        bg_photo=ai_data.get("bg_photo_bytes"),
        as_webp=True
    )

    sess(cb.from_user.id)["last_sticker"] = img
    if not is_admin:
        u["ai_used"] = int(u.get("ai_used", 0)) + 1

    await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
    await cb.message.answer(
        "از این استیکر راضی بودی؟",
        reply_markup=rate_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "ai:edit")
async def on_ai_edit(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    await cb.message.answer(
        "موقعیت عمودی متن:",
        reply_markup=ai_vpos_kb()
    )
    await cb.answer()

@router.callback_query(F.data == "rate:yes")
async def on_rate_yes(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    sticker_bytes = s.get("last_sticker")
    pack_short_name = s.get("current_pack_short_name")
    pack_title = s.get("current_pack_title")

    if not sticker_bytes or not pack_short_name:
        await cb.message.answer("خطایی در پیدا کردن پک یا استیکر رخ داد. لطفا دوباره تلاش کنید.", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()
        return

    if len(sticker_bytes) > 64 * 1024:
        await cb.message.answer("فایل استیکر خیلی بزرگ است. لطفا با متن کوتاه‌تر یا ساده‌تر دوباره تلاش کنید.", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()
        return
    
    await cb.message.answer("در حال افزودن استیکر به پک، لطفا چند لحظه صبر کنید...")
    await asyncio.sleep(1.5)

    try:
        sticker_to_add = InputSticker(
            sticker=BufferedInputFile(sticker_bytes, filename="sticker.webp"),
            emoji_list=["😄"],
            format="static"
        )
        await cb.bot.add_sticker_to_set(
            user_id=cb.from_user.id,
            name=pack_short_name,
            sticker=sticker_to_add
        )
        
        pack_link = f"https://t.me/addstickers/{pack_short_name}"
        await cb.message.answer(f"استیکر با موفقیت به پک «{pack_title}» افزوده شد.\n\n{pack_link}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        
    except TelegramBadRequest as e:
        await cb.message.answer(f"خطا در افزودن استیکر به پک: {escape(e.message)}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    except Exception as e:
        traceback.print_exc()
        await cb.message.answer(f"خطای غیرمنتظره‌ای رخ داد. لطفا به ادمین اطلاع دهید.\nخطا: {escape(str(e))}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))

    await cb.answer()

@router.callback_query(F.data == "rate:no")
async def on_rate_no(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    sess(cb.from_user.id)["await_feedback"] = True
    await cb.message.answer("چه چیزی رو دوست نداشتی؟")
    await cb.answer()

@router.callback_query(F.data == "pack:skip")
async def on_pack_skip(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    await cb.message.answer(
        "باشه، اضافه نمی‌کنم.",
        reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
    )
    await cb.answer()

@router.callback_query(F.data == "pack:start_creation")
async def on_pack_start_creation(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    mode = s.get("pack_wizard", {}).get("mode", "simple")
    s["pack_wizard"] = {"step": "awaiting_name", "mode": mode}
    rules_text = (
        "برای ایجاد پک جدید، یک نام انگلیسی ارسال کنید.\n\n"
        "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
        "• حداکثر ۵۰ کاراکتر"
    )
    await cb.message.answer(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "pack:select_existing")
async def on_pack_select_existing(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    mode = s.get("pack_wizard", {}).get("mode", "simple")
    
    await cb.message.answer(
        "کدام پک را انتخاب می‌کنید؟",
        reply_markup=pack_selection_kb(cb.from_user.id, mode)
    )
    await cb.answer()

@router.message()
async def on_message(message: Message, bot: Bot):
    uid = message.from_user.id
    s = sess(uid)
    is_admin = (uid == ADMIN_ID)
    
    if not await require_channel_membership(message, bot):
        return

    if is_admin and s["admin"].get("action"):
        action = s["admin"]["action"]
        if action == "broadcast":
            s["admin"]["action"] = None
            success_count = 0
            for user_id in USERS:
                try:
                    await message.bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
                    success_count += 1
                except Exception:
                    pass
            await message.answer(f"پیام همگانی با موفقیت به {success_count} کاربر ارسال شد.")
            return

        if action == "dm_get_user":
            if message.text and message.text.isdigit():
                target_uid = int(message.text)
                s["admin"]["target_uid"] = target_uid
                s["admin"]["action"] = "dm_get_text"
                await message.answer(f"پیام خود را برای ارسال به کاربر {target_uid} بنویسید:")
            else:
                await message.answer("آیدی عددی نامعتبر است. لطفا دوباره تلاش کنید.")
            return

        if action == "dm_get_text":
            target_uid = s["admin"].get("target_uid")
            s["admin"]["action"] = None
            try:
                await message.bot.copy_message(chat_id=target_uid, from_chat_id=message.chat.id, message_id=message.message_id)
                await message.answer(f"پیام به کاربر {target_uid} ارسال شد.")
            except Exception as e:
                await message.answer(f"خطا در ارسال پیام: {escape(str(e))}")
            return

        if action == "quota_get_user":
            if message.text and message.text.isdigit():
                target_uid = int(message.text)
                s["admin"]["target_uid"] = target_uid
                s["admin"]["action"] = "quota_get_value"
                await message.answer(f"سهمیه جدید برای کاربر {target_uid} را وارد کنید (مثال: 10):")
            else:
                await message.answer("آیدی عددی نامعتبر است. لطفا دوباره تلاش کنید.")
            return

        if action == "quota_get_value":
            target_uid = s["admin"].get("target_uid")
            s["admin"]["action"] = None
            if message.text and message.text.isdigit():
                new_quota = int(message.text)
                if target_uid in USERS:
                    USERS[target_uid]["daily_limit"] = new_quota
                    await message.answer(f"سهمیه کاربر {target_uid} به {new_quota} تغییر یافت.")
                else:
                    await message.answer("کاربر مورد نظر در سیستم یافت نشد.")
            else:
                await message.answer("مقدار سهمیه نامعتبر است. لطفا یک عدد وارد کنید.")
            return

    if s.get("await_feedback") and message.text:
        s["await_feedback"] = False
        await message.answer(
            "ممنون از بازخوردت",
            reply_markup=back_to_menu_kb(is_admin)
        )
        return

    pack_wizard = s.get("pack_wizard", {})
    if pack_wizard.get("step") == "awaiting_name" and message.text:
        global BOT_USERNAME

        if not BOT_USERNAME:
            bot_info = await message.bot.get_me()
            BOT_USERNAME = bot_info.username

        pack_name = message.text.strip()

        pack_name_lower = pack_name.lower()
        if any(word in pack_name_lower for word in FORBIDDEN_WORDS):
            await message.answer(
                "نام پک انتخاب شده نامناسب است. لطفاً از کلمات مناسبی و بدون کاراکترهای خاص استفاده کنید.",
                reply_markup=back_to_menu_kb(is_admin)
            )
            return

        if not is_valid_pack_name(pack_name):
            await message.answer(
                "نام پک نامعتبر است. لطفا طبق قوانین یک نام جدید انتخاب کنید:\n\n"
                "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
                "• باید با حرف شروع شود\n"
                "• نباید با زیرخط تمام شود\n"
                "• نباید دو زیرخط پشت سر هم داشته باشد\n"
                "• حداکثر ۵۰ کاراکتر",
                reply_markup=back_to_menu_kb(is_admin)
            )
            return

        short_name = f"{pack_name}_by_{BOT_USERNAME}"
        mode = pack_wizard.get("mode")

        if len(short_name) > 64:
            await message.answer(
                f"نام پک خیلی طولانی است. با افزودن '_by_{BOT_USERNAME}' به {len(short_name)} کاراکتر می‌رسد.\n"
                "لطفا یک نام کوتاه‌تر انتخاب کنید.",
                reply_markup=back_to_menu_kb(is_admin)
            )
            return

        try:
            pack_exists = await check_pack_exists(message.bot, short_name)

            if pack_exists:
                s["current_pack_short_name"] = short_name
                s["current_pack_title"] = pack_name
                s["pack_wizard"] = {}
                add_user_pack(uid, pack_name, short_name)
                await message.answer(f"استیکرها به پک موجود «{pack_name}» افزوده خواهند شد.")
            else:
                dummy_img = render_image("First", "center", "center", "Default", "#FFFFFF", "medium", as_webp=True)
                sticker_to_add = InputSticker(
                    sticker=BufferedInputFile(dummy_img, filename="sticker.webp"),
                    emoji_list=["🎉"],
                    format="static"
                )
                try:
                    await message.bot.create_new_sticker_set(
                        user_id=uid,
                        name=short_name,
                        title=pack_name,
                        stickers=[sticker_to_add],
                        sticker_type='regular'
                    )
                except pydantic_core.ValidationError as e:
                    if "result.is_animated" in str(e) and "result.is_video" in str(e):
                        print(f"Ignoring known aiogram validation error for pack {short_name}")
                    else:
                        raise e
                
                s["current_pack_short_name"] = short_name
                s["current_pack_title"] = pack_name
                s["pack_wizard"] = {}
                add_user_pack(uid, pack_name, short_name)
                pack_link = f"https://t.me/addstickers/{short_name}"
                await message.answer(f"پک استیکر «{pack_name}» با موفقیت ساخته شد!\n\n{pack_link}\n\nحالا استیکر بعدی خود را بسازید.")

            if mode == "simple":
                s["mode"] = "simple"
                s["simple"] = {"text": None, "bg_mode": "transparent", "bg_photo_bytes": None}
                await message.answer("متن استیکر ساده رو بفرست:", reply_markup=back_to_menu_kb(is_admin))
            elif mode == "ai":
                s["mode"] = "ai"
                s["ai"] = {
                    "text": None, "v_pos": "center", "h_pos": "center", "font": "Default",
                    "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None
                }
                await message.answer("نوع استیکر پیشرفته را انتخاب کنید:", reply_markup=ai_type_kb())

        except TelegramBadRequest as e:
            error_msg = e.message.lower()
            if "invalid sticker set name" in error_msg or "bad request" in error_msg:
                await message.answer(
                    f"نام پک نامعتبر است. خطا: {escape(e.message)}\n\n"
                    "لطفا یک نام دیگر انتخاب کنید که:\n"
                    "• فقط شامل حروف انگلیسی کوچک، عدد و زیرخط باشد\n"
                    "• با حرف شروع شود\n"
                    "• کوتاه‌تر باشد",
                    reply_markup=back_to_menu_kb(is_admin)
                )
            else:
                await message.answer(f"خطا در ساخت پک: {escape(e.message)}", reply_markup=back_to_menu_kb(is_admin))
        except Exception as e:
            await message.answer(f"خطای غیرمنتظره: {escape(str(e))}", reply_markup=back_to_menu_kb(is_admin))
            return

    if message.photo:
        if s.get("mode") == "simple" and s["simple"].get("awaiting_bg_photo"):
            file = await message.bot.download(message.photo[-1].file_id)
            s["simple"]["bg_photo_bytes"] = file.read()
            s["simple"]["awaiting_bg_photo"] = False
            if s["simple"].get("text"):
                img = render_image(
                    text=s["simple"]["text"],
                    v_pos="center",
                    h_pos="center",
                    font_key="Default",
                    color_hex="#FFFFFF",
                    size_key="medium",
                    bg_photo=s["simple"]["bg_photo_bytes"],
                    as_webp=False
                )
                await message.answer_photo(BufferedInputFile(img, "preview.png"), caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
            else:
                await message.answer("عکس دریافت شد. حالا متن را بفرستید:")
        elif s.get("mode") == "ai" and s["ai"].get("awaiting_bg_photo"):
            file = await message.bot.download(message.photo[-1].file_id)
            s["ai"]["bg_photo_bytes"] = file.read()
            s["ai"]["awaiting_bg_photo"] = False
            await message.answer("عکس دریافت شد. حالا متن را بفرستید:")
        return

    if message.video and s.get("mode") == "ai" and s["ai"].get("sticker_type") == "video":
        await message.answer("در حال پردازش ویدیو...")
        file = await message.bot.download(message.video.file_id)
        webm_bytes = await process_video_to_webm(file.read())

        if webm_bytes:
            sess(uid)["last_sticker"] = webm_bytes
            await message.answer_sticker(BufferedInputFile(webm_bytes, "sticker.webm"))
            await message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
        else:
            await message.answer("پردازش ویدیو با خطا مواجه شد.", reply_markup=back_to_menu_kb(is_admin))
        return

    mode = s.get("mode", "menu")

    if mode == "simple":
        if message.text:
            s["simple"]["text"] = message.text.strip()
            await message.answer("پس‌زمینه رو انتخاب کن:", reply_markup=simple_bg_kb())
    elif mode == "ai":
        if message.text and s["ai"].get("sticker_type") == "image":
            u = user(uid)
            left = _quota_left(u, is_admin)
            if left <= 0 and not is_admin:
                await message.answer("سهمیه امروز تمام شد!", reply_markup=back_to_menu_kb(is_admin))
                return
            s["ai"]["text"] = message.text.strip()
            await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
    else:
        is_admin = (uid == ADMIN_ID)
        await message.answer("از منوی زیر انتخاب کن:", reply_markup=main_menu_kb(is_admin))
