# Vercel-compatible bot handlers
"""
Bot handlers for all message and callback interactions
"""
from aiogram import Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
import asyncio
from html import escape

from .bot_logic import (
    router, USERS, SESSIONS, ADMIN_PENDING, BOT_USERNAME,
    user, sess, reset_mode, get_user_packs, add_user_pack, set_current_pack, get_current_pack,
    render_image, check_channel_membership, require_channel_membership,
    main_menu_kb, back_to_menu_kb, simple_bg_kb, after_preview_kb, rate_kb,
    pack_selection_kb, add_to_pack_kb, ai_type_kb, ai_image_source_kb,
    ai_font_kb, ai_vpos_kb, ai_hpos_kb, admin_panel_kb,
    check_pack_exists, is_valid_pack_name, process_video_to_webm,
    is_ffmpeg_installed, ADMIN_ID, FORBIDDEN_WORDS, DEFAULT_PALETTE, NAME_TO_HEX, POS_WORDS, SIZE_WORDS,
    _quota_left
)
from aiogram.types import BufferedInputFile, InputSticker
import pydantic_core
import traceback

# ... (Standard handlers like on_check_membership, on_home, etc. remain the same) ...
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
    await cb.message.edit_text(
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
    await cb.message.edit_text("پنل ادمین:", reply_markup=admin_panel_kb())
    await cb.answer()

@router.callback_query(F.data == "admin:broadcast")
async def on_admin_broadcast(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "broadcast"
    await cb.message.edit_text("پیام همگانی خود را ارسال کنید. برای انصراف /cancel را بفرستید.")
    await cb.answer()

@router.callback_query(F.data == "admin:dm_prompt")
async def on_admin_dm_prompt(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "dm_get_user"
    await cb.message.edit_text("آیدی عددی کاربر مورد نظر را ارسال کنید. برای انصراف /cancel را بفرستید.")
    await cb.answer()

@router.callback_query(F.data == "admin:quota_prompt")
async def on_admin_quota_prompt(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    s = sess(cb.from_user.id)
    s["admin"]["action"] = "quota_get_user"
    await cb.message.edit_text("آیدی عددی کاربر مورد نظر را برای تغییر سهمیه ارسال کنید. برای انصراف /cancel را بفرستید.")
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
    await cb.message.edit_text(help_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:support")
async def on_support(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot):
        return
        
    from .bot_logic import SUPPORT_USERNAME
    await cb.message.edit_text(
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
    await cb.message.edit_text(
        f"سهمیه امروز: {quota_txt}",
        reply_markup=back_to_menu_kb(is_admin)
    )
    await cb.answer()
@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    s = sess(cb.from_user.id)
    uid = cb.from_user.id
    user_packs = get_user_packs(uid)

    # Set mode right away
    s["mode"] = "simple"
    s["simple"] = {} # Reset simple state

    if user_packs:
        s["pack_wizard"] = {"mode": "simple"}
        await cb.message.edit_text("می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟", reply_markup=pack_selection_kb(uid, "simple"))
    else:
        s["pack_wizard"] = {"step": "awaiting_name", "mode": "simple"}
        await cb.message.edit_text("ابتدا باید یک پک استیکر بسازید. نام پک را بنویسید (فقط حروف انگلیسی و اعداد):", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:ai")
async def on_ai(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)
    if left <= 0 and not is_admin:
        await cb.message.edit_text("سهمیه استیکرساز پیشرفته شما تمام شده است. می‌توانید از استیکرساز ساده استفاده کنید.", reply_markup=back_to_menu_kb(is_admin))
        await cb.answer()
        return

    s = sess(cb.from_user.id)
    uid = cb.from_user.id
    user_packs = get_user_packs(uid)

    # Set mode right away
    s["mode"] = "ai"
    s["ai"] = {} # Reset ai state

    if user_packs:
        s["pack_wizard"] = {"mode": "ai"}
        await cb.message.edit_text("می‌خواهید استیکر جدید را به کدام پک اضافه کنید؟", reply_markup=pack_selection_kb(uid, "ai"))
    else:
        s["pack_wizard"] = {"step": "awaiting_name", "mode": "ai"}
        await cb.message.edit_text("ابتدا باید یک پک استیکر بسازید. نام پک را بنویسید (فقط حروف انگلیسی و اعداد):", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("pack:select:"))
async def on_pack_select(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    pack_short_name = cb.data.split(":")[-1]
    uid = cb.from_user.id
    s = sess(uid)
    mode = s.get("pack_wizard", {}).get("mode", "simple")

    set_current_pack(uid, pack_short_name)
    s["pack_wizard"] = {} # Clear pack wizard state
    
    if mode == "simple":
        s["simple"]["awaiting_text"] = True
        await cb.message.edit_text("متن استیکر ساده رو بفرست:", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    elif mode == "ai":
        s["ai"]["awaiting_text"] = True
        await cb.message.edit_text("متن استیکر پیشرفته رو بفرست:", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("pack:new:"))
async def on_pack_new(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    mode = cb.data.split(":")[-1]
    s = sess(cb.from_user.id)
    s["pack_wizard"] = {"step": "awaiting_name", "mode": mode}
    await cb.message.edit_text("نام پک جدید را بنویسید (فقط حروف انگلیسی و اعداد):", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("simple:bg:"))
async def on_simple_bg(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    s = sess(cb.from_user.id)
    if "simple" not in s: return # Safety check

    mode = cb.data.split(":")[-1]
    if mode == "photo_prompt":
        s["simple"]["awaiting_bg_photo"] = True
        await cb.message.edit_text("عکس مورد نظر برای پس‌زمینه را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    else:
        s["simple"]["bg_mode"] = mode
        s["simple"]["bg_photo_bytes"] = None
        img = render_image(
            text=s["simple"]["text"], v_pos="center", h_pos="center", font_key="Default",
            color_hex="#FFFFFF", size_key="medium", bg_mode=mode,
            bg_photo=s.get("simple", {}).get("bg_photo_bytes"), as_webp=False
        )
        # Delete the menu before sending photo
        await cb.message.delete()
        await cb.message.answer_photo(BufferedInputFile(img, "preview.png"), caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
    await cb.answer()

# ... (rest of the handlers from the most complete version) ...
@router.callback_query(F.data.startswith("ai:font:"))
async def on_ai_font(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    font = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["font"] = font
    await cb.message.edit_text("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ai:vpos:"))
async def on_ai_vpos(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    v_pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["v_pos"] = v_pos
    await cb.message.edit_text("موقعیت افقی متن:", reply_markup=ai_hpos_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("ai:hpos:"))
async def on_ai_hpos(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    h_pos = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["h_pos"] = h_pos
    kb = InlineKeyboardBuilder()
    for name, hx in DEFAULT_PALETTE:
        kb.button(text=name, callback_data=f"ai:color:{hx}")
    kb.adjust(4)
    await cb.message.edit_text("رنگ متن:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:color:")))
async def on_ai_color(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    color = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["color"] = color
    kb = InlineKeyboardBuilder()
    for label, val in [("کوچک", "small"), ("متوسط", "medium"), ("بزرگ", "large")]:
        kb.button(text=label, callback_data=f"ai:size:{val}")
    kb.adjust(3)
    await cb.message.edit_text("اندازه فونت:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data.startswith("ai:bold:"))
async def on_ai_bold(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    bold_status = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["bold"] = (bold_status == "yes")
    ai_data = sess(cb.from_user.id)["ai"]
    img = render_image(
        text=ai_data["text"], v_pos=ai_data["v_pos"], h_pos=ai_data["h_pos"],
        font_key=ai_data["font"], color_hex=ai_data["color"], size_key=ai_data["size"],
        bg_photo=ai_data.get("bg_photo_bytes"), as_webp=False, bold=ai_data["bold"]
    )
    await cb.message.delete()
    await cb.message.answer_photo(BufferedInputFile(img, "preview.png"), caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("ai"))
    await cb.answer()

@router.callback_query(F.data.func(lambda d: d and d.startswith("ai:size:")))
async def on_ai_size(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    size = cb.data.split(":")[-1]
    sess(cb.from_user.id)["ai"]["size"] = size
    kb = InlineKeyboardBuilder()
    kb.button(text="بله", callback_data="ai:bold:yes")
    kb.button(text="خیر", callback_data="ai:bold:no")
    kb.adjust(2)
    await cb.message.edit_text("فونت بولد (ضخیم) باشد؟", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(F.data == "ai:confirm")
# ... (confirm handlers need to be restored as well) ...
@router.callback_query(F.data == "ai:edit")
async def on_ai_edit(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    await cb.message.edit_text("فونت را انتخاب کنید:", reply_markup=ai_font_kb())
    await cb.answer()
@router.callback_query(F.data == "simple:confirm")
async def on_simple_confirm(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    s = sess(cb.from_user.id)
    simple_data = s["simple"]
    img = render_image(
        text=simple_data["text"], v_pos="center", h_pos="center",
        font_key="Default", color_hex="#FFFFFF", size_key="medium",
        bg_mode=simple_data.get("bg_mode", "transparent"),
        bg_photo=simple_data.get("bg_photo_bytes"), as_webp=True
    )
    s["last_sticker"] = img
    await cb.message.delete()
    await cb.message.answer_sticker(BufferedInputFile(img, filename="sticker.webp"))
    await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
    await cb.answer()

@router.callback_query(F.data == "simple:edit")
async def on_simple_edit(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    await cb.message.edit_text("پس‌زمینه رو انتخاب کن:", reply_markup=simple_bg_kb())
    await cb.answer()
# ... (on_message handler needs to be fully restored) ...
@router.message()
async def on_message(message: Message, bot: Bot):
    uid = message.from_user.id
    s = sess(uid)
    is_admin = (uid == ADMIN_ID)
    
    if not await require_channel_membership(message, bot): return

    # Admin actions
    if is_admin and s["admin"].get("action"):
        # ... (admin action code remains the same) ...
        return

    # Pack creation
    pack_wizard = s.get("pack_wizard", {})
    if pack_wizard.get("step") == "awaiting_name" and message.text:
        global BOT_USERNAME

        if not BOT_USERNAME:
            bot_info = await message.bot.get_me()
            BOT_USERNAME = bot_info.username

        pack_name = message.text.strip()

        # ... (rest of pack creation logic) ...
        short_name = f"{pack_name}_by_{BOT_USERNAME}"
        mode = pack_wizard.get("mode")

        try:
            # Create or select pack
            # ...

            # Start sticker creation flow
            if mode == "simple":
                s["mode"] = "simple"
                s["simple"] = {"awaiting_text": True}
                await message.answer(f"پک «{pack_name}» انتخاب شد. حالا متن استیکر ساده رو بفرست:", reply_markup=back_to_menu_kb(is_admin))
            elif mode == "ai":
                s["mode"] = "ai"
                s["ai"] = {"awaiting_text": True}
                await message.answer(f"پک «{pack_name}» انتخاب شد. حالا متن استیکر پیشرفته رو بفرست:", reply_markup=back_to_menu_kb(is_admin))

        except Exception as e:
            await message.answer(f"خطا در ساخت پک: {escape(str(e))}", reply_markup=back_to_menu_kb(is_admin))
        return

    # Text input for stickers
    mode = s.get("mode")
    if mode == "simple" and s.get("simple", {}).get("awaiting_text"):
        s["simple"]["text"] = message.text
        s["simple"]["awaiting_text"] = False
        await message.answer("پس‌زمینه رو انتخاب کن:", reply_markup=simple_bg_kb())
        return

    if mode == "ai" and s.get("ai", {}).get("awaiting_text"):
        s["ai"]["text"] = message.text
        s["ai"]["awaiting_text"] = False
        await message.answer("فونت را انتخاب کنید:", reply_markup=ai_font_kb())
        return

    # Fallback
    await message.answer("از منوی زیر انتخاب کن:", reply_markup=main_menu_kb(is_admin))
