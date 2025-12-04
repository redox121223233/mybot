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

# Standard handlers
@router.callback_query(F.data == "check_membership")
async def on_check_membership(cb: CallbackQuery, bot: Bot):
    is_member = await check_channel_membership(bot, cb.from_user.id)
    if is_member:
        await cb.message.edit_text(
            "عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.",
            reply_markup=main_menu_kb(cb.from_user.id == ADMIN_ID)
        )
    else:
        await cb.answer("شما هنوز در کانال عضو نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
    await cb.answer()

@router.callback_query(F.data == "menu:home")
async def on_home(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    reset_mode(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    await cb.message.edit_text("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
    await cb.answer()

@router.callback_query(F.data == "menu:simple")
async def on_simple(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    s = sess(cb.from_user.id)
    uid = cb.from_user.id
    user_packs = get_user_packs(uid)

    if user_packs:
        s["pack_wizard"] = {"mode": "simple"}
        await cb.message.edit_text(
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
            "• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)"
        )
        await cb.message.edit_text(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "menu:ai")
async def on_ai(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    u = user(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    left = _quota_left(u, is_admin)

    if left <= 0 and not is_admin:
        await cb.message.edit_text("سهمیه امروز تمام شد!", reply_markup=back_to_menu_kb(is_admin))
        await cb.answer()
        return

    s = sess(cb.from_user.id)
    uid = cb.from_user.id
    user_packs = get_user_packs(uid)

    if user_packs:
        s["pack_wizard"] = {"mode": "ai"}
        await cb.message.edit_text(
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
            "• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)"
        )
        await cb.message.edit_text(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("pack:select:"))
async def on_pack_select(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
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
        
        mode = s.get("pack_wizard", {}).get("mode", "simple")
        s["pack_wizard"] = {} # Clear wizard after getting mode
        
        if mode == "simple":
            s["mode"] = "simple"
            s["simple"] = {"text": None, "bg_mode": "transparent", "bg_photo_bytes": None}
            await cb.message.edit_text(
                f"پک «{selected_pack['name']}» انتخاب شد.\n\nمتن استیکر ساده رو بفرست:",
                reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
            )
        elif mode == "ai":
            s["mode"] = "ai"
            s["ai"] = {
                "text": None, "v_pos": "center", "h_pos": "center", "font": "Default",
                "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None
            }
            await cb.message.edit_text(
                f"پک «{selected_pack['name']}» انتخاب شد.\n\nنوع استیکر پیشرفته را انتخاب کنید:",
                reply_markup=ai_type_kb()
            )
    await cb.answer()

@router.callback_query(F.data.startswith("pack:new:"))
async def on_pack_new(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    mode = cb.data.split(":")[-1]
    s = sess(cb.from_user.id)
    s["pack_wizard"] = {"step": "awaiting_name", "mode": mode}
    rules_text = (
        "برای ایجاد پک جدید، یک نام انگلیسی ارسال کنید.\n\n"
        "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
        "• حداکثر ۵۰ کاراکتر"
    )
    await cb.message.edit_text(rules_text, reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data.startswith("simple:bg:"))
async def on_simple_bg(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    s = sess(cb.from_user.id)
    if "simple" not in s or "text" not in s["simple"]:
        await cb.answer("لطفا ابتدا متن استیکر را ارسال کنید.", show_alert=True)
        return
        
    s_simple = s["simple"]
    mode = cb.data.split(":")[-1]
    if mode == "photo_prompt":
        s_simple["awaiting_bg_photo"] = True
        await cb.message.edit_text("عکس مورد نظر برای پس‌زمینه را ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    else:
        s_simple["bg_mode"] = mode
        s_simple["bg_photo_bytes"] = None
        img = render_image(
            text=s_simple["text"], v_pos="center", h_pos="center", font_key="Default",
            color_hex="#FFFFFF", size_key="medium", bg_mode=mode,
            bg_photo=s_simple.get("bg_photo_bytes"), as_webp=False
        )
        await cb.message.delete()
        await cb.message.answer_photo(BufferedInputFile(img, "preview.png"), caption="پیش‌نمایش آماده است", reply_markup=after_preview_kb("simple"))
    await cb.answer()

@router.callback_query(F.data.startswith("ai:type:"))
async def on_ai_type(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    sticker_type = cb.data.split(":")[-1]
    s = sess(cb.from_user.id)
    s["ai"]["sticker_type"] = sticker_type

    if sticker_type == "image":
        await cb.message.edit_text("منبع استیکر تصویری را انتخاب کنید:", reply_markup=ai_image_source_kb())
    elif sticker_type == "video":
        if not is_ffmpeg_installed():
            await cb.message.edit_text(
                "قابلیت ویدیو فعال نیست.",
                reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID)
            )
        else:
            await cb.message.edit_text("یک فایل ویدیو ارسال کنید:", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

@router.callback_query(F.data == "rate:yes")
async def on_rate_yes(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    s = sess(cb.from_user.id)
    sticker_bytes = s.get("last_sticker")
    pack_short_name = s.get("current_pack_short_name")
    pack_title = s.get("current_pack_title")

    if not sticker_bytes or not pack_short_name:
        await cb.message.answer("خطایی در پیدا کردن پک یا استیکر رخ داد. لطفا دوباره تلاش کنید.", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        await cb.answer()
        return

    await cb.message.edit_text("در حال افزودن استیکر به پک، لطفا چند لحظه صبر کنید...")
    await asyncio.sleep(1.5)

    try:
        sticker_to_add = InputSticker(
            sticker=BufferedInputFile(sticker_bytes, filename="sticker.webp"),
            emoji_list=["😂"],
            format='static'
        )
        await bot.add_sticker_to_set(
            user_id=cb.from_user.id,
            name=pack_short_name,
            sticker=sticker_to_add
        )
        
        pack_link = f"https://t.me/addstickers/{pack_short_name}"
        await cb.message.answer(f"استیکر با موفقیت به پک «{pack_title}» اضافه شد.\n\n{pack_link}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
        
    except TelegramBadRequest as e:
        await cb.message.answer(f"خطا در افزودن استیکر به پک: {e.message}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))
    except Exception as e:
        traceback.print_exc()
        await cb.message.answer(f"خطای غیرمنتظره‌ای رخ داد. لطفا به ادمین اطلاع دهید.\nخطا: {str(e)}", reply_markup=back_to_menu_kb(cb.from_user.id == ADMIN_ID))

    await cb.answer()

@router.message()
async def on_message(message: Message, bot: Bot):
    uid = message.from_user.id
    s = sess(uid)
    is_admin = (uid == ADMIN_ID)
    
    if not await require_channel_membership(message, bot): return

    # Admin actions handler (as in reference)
    # ...

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
                "نام پک انتخاب شده نامناسب است. لطفاً از کلمات مناسب و بدون کاراکترهای خاص استفاده کنید.",
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
                f"نام پک خیلی طولانی است. با اضافه شدن '_by_{BOT_USERNAME}' به {len(short_name)} کاراکتر می‌رسد.\n"
                "لطفا یک نام کوتاه‌تر انتخاب کنید.",
                reply_markup=back_to_menu_kb(is_admin)
            )
            return

        try:
            pack_exists = await check_pack_exists(message.bot, short_name)

            if pack_exists:
                s["current_pack_short_name"] = short_name
                s["current_pack_title"] = pack_name
                add_user_pack(uid, pack_name, short_name)
                await message.answer(f"استیکرها به پک موجود «{pack_name}» اضافه خواهند شد.")
            else:
                # Use as_webp=False to create a PNG for the first sticker
                dummy_img = render_image("First", "center", "center", "Default", "#FFFFFF", "medium", as_webp=False)
                sticker_to_add = InputSticker(
                    sticker=BufferedInputFile(dummy_img, filename="sticker.png"), # Use .png extension
                    emoji_list=["🎉"],
                    format='static'
                )
                try:
                    await message.bot.create_new_sticker_set(
                        user_id=uid, name=short_name, title=pack_name,
                        stickers=[sticker_to_add], sticker_format='static'
                    )
                except pydantic_core.ValidationError as e:
                    if "result.is_animated" in str(e) and "result.is_video" in str(e):
                        print(f"Ignoring known aiogram validation error for pack {short_name}")
                    else: raise e
                
                s["current_pack_short_name"] = short_name
                s["current_pack_title"] = pack_name
                add_user_pack(uid, pack_name, short_name)
                pack_link = f"https://t.me/addstickers/{short_name}"
                await message.answer(f"پک استیکر «{pack_name}» با موفقیت ساخته شد!\n\n{pack_link}\n\nحالا استیکر بعدی خود را بسازید.")

            s["pack_wizard"] = {} # Clear wizard state
            if mode == "simple":
                s["mode"] = "simple"
                s["simple"] = {"text": None, "bg_mode": "transparent", "bg_photo_bytes": None}
                await message.answer("متن استیکر ساده رو بفرست:", reply_markup=back_to_menu_kb(is_admin))
            elif mode == "ai":
                s["mode"] = "ai"
                s["ai"] = {"text": None, "v_pos": "center", "h_pos": "center", "font": "Default",
                           "color": "#FFFFFF", "size": "large", "bg_photo_bytes": None}
                await message.answer("نوع استیکر پیشرفته را انتخاب کنید:", reply_markup=ai_type_kb())

        except TelegramBadRequest as e:
            await message.answer(f"خطا در ساخت پک: {e.message}", reply_markup=back_to_menu_kb(is_admin))
        except Exception as e:
            await message.answer(f"خطای غیرمنتظره: {str(e)}", reply_markup=back_to_menu_kb(is_admin))
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
                await message.answer("سهمیه تمام شد!", reply_markup=back_to_menu_kb(is_admin))
                return
            s["ai"]["text"] = message.text.strip()
            await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
    else:
        is_admin = (uid == ADMIN_ID)
        await message.answer("از منوی زیر انتخاب کن:", reply_markup=main_menu_kb(is_admin))
