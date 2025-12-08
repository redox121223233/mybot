"""
Bot message and callback handlers, fully refactored from the reference script `bot (2).py`.
"""
import asyncio
import logging
import pydantic_core
import traceback
from aiogram import Bot, F

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputSticker
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# Import all necessary components explicitly
from .bot_logic import (
    router, SESSIONS, USERS, ADMIN_ID, SUPPORT_USERNAME, FORBIDDEN_WORDS,
    user, sess, reset_mode, _quota_left, _seconds_to_reset, _fmt_eta,
    get_user_packs, add_user_pack, set_current_pack, get_current_pack, is_valid_pack_name, check_pack_exists,
    render_image, is_ffmpeg_installed, process_video_to_webm,
    require_channel_membership, check_channel_membership,
    main_menu_kb, back_to_menu_kb, simple_bg_kb, after_preview_kb, rate_kb, pack_selection_kb,
    ai_type_kb, ai_image_source_kb, ai_vpos_kb, ai_hpos_kb, admin_panel_kb
)
from .config import DEFAULT_PALETTE, DAILY_LIMIT

async def safe_edit_text(cb: CallbackQuery, text: str, reply_markup=None, delete_if_no_text: bool = True):
    """
    Safely edit a message's text, handling the case where there's no text to edit.
    If delete_if_no_text is True and the message has no text, delete it and send a new message.
    """
    try:
        await cb.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "there is no text in the message to edit" in str(e) and delete_if_no_text:
            await cb.message.delete()
            await cb.message.answer(text, reply_markup=reply_markup)
        else:
            raise

# --- Core Handlers ---
@router.message(CommandStart())
async def on_start(message: Message, bot: Bot):
    if not await require_channel_membership(message, bot): return
    reset_mode(message.from_user.id)
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
    if not await require_channel_membership(cb.message, bot): return
    reset_mode(cb.from_user.id)
    await safe_edit_text(cb, "منوی اصلی:", reply_markup=main_menu_kb(cb.from_user.id == ADMIN_ID))
    await cb.answer()

# --- Menu Handlers ---
@router.callback_query(F.data.startswith("menu:"))
async def on_menu_selection(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    action = cb.data.split(":")[1]
    uid, is_admin = cb.from_user.id, cb.from_user.id == ADMIN_ID
    s = sess(uid)

    if action in ["simple", "ai"]:
        if action == "ai" and _quota_left(user(uid), is_admin) <= 0:
            await cb.answer("سهمیه امروز شما تمام شده است.", show_alert=True); return
        s["pack_wizard"] = {"mode": action}
        s["mode"] = action  # Also set mode at session level
        if get_user_packs(uid):
            await safe_edit_text(cb, "استیکر را به کدام پک اضافه می‌کنید؟", reply_markup=pack_selection_kb(uid, action))
        else:
            s["pack_wizard"]["step"] = "awaiting_name"
            await safe_edit_text(cb, "برای ساخت پک جدید، یک نام انگلیسی ارسال کنید.", reply_markup=back_to_menu_kb(is_admin))
    elif action == "quota":
        u = user(uid)
        left = _quota_left(u, is_admin)
        if is_admin:
            quota_text = f"\u0633\u0647\u0645\u06cc\u0647 \u0627\u0645\u0631\u0648\u0632 \u0634\u0645\u0627: \u0646\u0627\u0645\u062d\u062f\u0648\u062f"
        else:
            quota_text = f"\u0633\u0647\u0645\u06cc\u0647 \u0627\u0645\u0631\u0648\u0632 \u0634\u0645\u0627: {left} \u0627\u0632 {u.get('daily_limit', DAILY_LIMIT)}"
        if not is_admin and left <= 0:
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
        await safe_edit_text(cb, "پنل ادمین:", reply_markup=admin_panel_kb())
    await cb.answer()

# --- Sticker Pack Handlers ---
@router.callback_query(F.data.startswith("pack:"))
async def on_pack_actions(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    parts, uid, s = cb.data.split(":"), cb.from_user.id, sess(cb.from_user.id)
    action = parts[1]
    
    if action == "select":
        pack_short_name = parts[2]
        mode = parts[3] if len(parts) > 3 else "simple"  # Get mode from callback data
        pack = next((p for p in get_user_packs(uid) if p["short_name"] == pack_short_name), None)
        if pack:
            set_current_pack(uid, pack_short_name)
            s.update({
                "current_pack_short_name": pack_short_name, 
                "current_pack_title": pack["name"], 
                "pack_wizard": {},
                "mode": mode  # Explicitly set the mode
            })
            logger.info(f"User {uid} selected pack {pack['name']} in {mode} mode")
            if mode == "simple":
                s.update({"simple": {}})  # Reset simple state
                await safe_edit_text(cb, f"پک «{pack['name']}» انتخاب شد. متن را بفرستید.")
            else:  # AI mode
                s.update({"ai": {}})  # Reset AI state
                await safe_edit_text(cb, f"پک «{pack['name']}» انتخاب شد. نوع استیکر؟", reply_markup=ai_type_kb())
    elif action == "new":
        s["pack_wizard"] = {"step": "awaiting_name", "mode": parts[2]}
        rules_text = (
            "نام پک را بنویس (مثال: my_stickers):\n\n"
            "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
            "• باید با حرف شروع شود\n"
            "• نباید با زیرخط تمام شود\n"
            "• نباید دو زیرخط پشت سر هم داشته باشد\n"
            "• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)"
        )
        await safe_edit_text(cb, rules_text)
    elif action == "start_creation":
        s["pack_wizard"] = {"step": "awaiting_name", "mode": s.get("pack_wizard",{}).get("mode", "simple")}
        rules_text = (
            "نام پک را بنویس (مثال: my_stickers):\n\n"
            "• فقط حروف انگلیسی کوچک، عدد و زیرخط\n"
            "• باید با حرف شروع شود\n"
            "• نباید با زیرخط تمام شود\n"
            "• نباید دو زیرخط پشت سر هم داشته باشد\n"
            "• حداکثر ۵۰ کاراکتر (به خاطر اضافه شدن نام ربات)"
        )
        await safe_edit_text(cb, rules_text)
    await cb.answer()

# --- Simple Sticker Creation ---
@router.callback_query(F.data.startswith("simple:"))
async def on_simple_actions(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    action = cb.data.split(":")[1]
    s, uid = sess(cb.from_user.id), cb.from_user.id
    simple_data = s["simple"]

    if action == "bg":
        bg_mode = cb.data.split(":")[-1]
        simple_data["bg_mode"] = bg_mode
        logger.info(f"User {cb.from_user.id} selected bg_mode: {bg_mode}, text: {simple_data.get('text', 'None')}")
        if bg_mode == "photo_prompt":
            simple_data["awaiting_bg_photo"] = True
            await safe_edit_text(cb, "عکس پس‌زمینه را ارسال کنید.")
        else:
            img = render_image(simple_data["text"], "center", "center", "Default", "#FFFFFF", "medium", bg_mode=bg_mode)
            await cb.message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("simple"))
    elif action == "confirm":
        img = render_image(simple_data["text"], "center", "center", "Default", "#FFFFFF", "medium", bg_mode=simple_data.get("bg_mode", "transparent"), bg_photo=simple_data.get("bg_photo_bytes"), as_webp=True)
        s["last_sticker"] = img
        await cb.message.answer_sticker(BufferedInputFile(img, "s.webp"))
        await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
    elif action == "edit":
        await safe_edit_text(cb, "پس‌زمینه رو انتخاب کن:", reply_markup=simple_bg_kb())
    await cb.answer()

# --- AI Sticker Creation ---
@router.callback_query(F.data.startswith("ai:"))
async def on_ai_actions(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    parts, uid, s = cb.data.split(":"), cb.from_user.id, sess(cb.from_user.id)
    action, ai_data = parts[1], s["ai"]

    if action == "type": ai_data["sticker_type"] = parts[2]; await safe_edit_text(cb, "منبع استیکر؟", reply_markup=ai_image_source_kb())
    elif action == "source":
        if parts[2] == "text": await safe_edit_text(cb, "متن استیکر را بفرست:")
        else: ai_data["awaiting_bg_photo"] = True; await safe_edit_text(cb, "عکس را ارسال کنید:")
    elif action == "vpos": ai_data["v_pos"] = parts[2]; await safe_edit_text(cb, "موقعیت افقی؟", reply_markup=ai_hpos_kb())
    elif action == "hpos": ai_data["h_pos"] = parts[2]; kb = InlineKeyboardBuilder(); [kb.button(text=n, callback_data=f"ai:color:{h}") for n,h in DEFAULT_PALETTE]; kb.adjust(4); await safe_edit_text(cb, "رنگ متن؟", reply_markup=kb.as_markup())
    elif action == "color": ai_data["color"] = parts[2]; kb = InlineKeyboardBuilder(); [kb.button(text=l, callback_data=f"ai:size:{v}") for l,v in [("کوچک","small"),("متوسط","medium"),("بزرگ","large")]]; kb.adjust(3); await safe_edit_text(cb, "اندازه فونت؟", reply_markup=kb.as_markup())
    elif action in ["size", "edit"]:
        if action == "size": ai_data["size"] = parts[2]
        img = render_image(ai_data.get("text","متن نمونه"), ai_data["v_pos"], ai_data["h_pos"], ai_data.get("font","Default"), ai_data["color"], ai_data["size"], bg_photo=ai_data.get("bg_photo_bytes"))
        await cb.message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("ai"))
    elif action == "confirm":
        if _quota_left(user(uid), uid==ADMIN_ID) <= 0: await cb.answer("سهمیه تمام شد!", show_alert=True); return
        img = render_image(ai_data["text"], ai_data["v_pos"], ai_data["h_pos"], ai_data.get("font","Default"), ai_data["color"], ai_data["size"], bg_photo=ai_data.get("bg_photo_bytes"), as_webp=True)
        s["last_sticker"] = img; user(uid)["ai_used"] = user(uid).get("ai_used", 0) + 1
        await cb.message.answer_sticker(BufferedInputFile(img, "s.webp"))
        await cb.message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
    await cb.answer()

# --- Sticker Confirmation and Rating ---
@router.callback_query(F.data.startswith("rate:"))
async def on_rate_actions(cb: CallbackQuery, bot: Bot):
    if not await require_channel_membership(cb.message, bot): return
    action, uid, s = cb.data.split(":")[1], cb.from_user.id, sess(cb.from_user.id)

    if action == "yes":
        sticker_bytes, pack_name, pack_title = s.get("last_sticker"), s.get("current_pack_short_name"), s.get("current_pack_title")
        logger.info(f"Adding sticker - User: {uid}, Pack: {pack_name}, Title: {pack_title}")
        logger.info(f"Session state: {s}")
        
        if not all([sticker_bytes, pack_name, pack_title]):
            logger.error(f"Missing data - sticker_bytes: {bool(sticker_bytes)}, pack_name: {bool(pack_name)}, pack_title: {bool(pack_title)}")
            await safe_edit_text(cb, "خطا: اطلاعات پک یافت نشد.", reply_markup=back_to_menu_kb(uid == ADMIN_ID)); return
            
        await safe_edit_text(cb, "در حال افزودن به پک...")
        try:
            # Convert to PNG format for pack addition (Telegram requires PNG for static stickers)
            from .bot_logic import render_image
            png_bytes = None
            current_mode = s.get("mode", "simple")
            
            if current_mode == "simple":
                simple_data = s.get("simple", {})
                png_bytes = render_image(
                    simple_data.get("text", "text"), "center", "center", "Default", "#FFFFFF", "medium", 
                    bg_mode=simple_data.get("bg_mode", "transparent"), 
                    bg_photo=simple_data.get("bg_photo_bytes"), 
                    as_webp=False  # Force PNG for pack
                )
            else:  # AI mode
                # Reset AI mode state for next sticker
                ai_data = s.get("ai", {})
                png_bytes = render_image(
                    ai_data.get("text", "text"), ai_data.get("v_pos", "center"), ai_data.get("h_pos", "center"), 
                    ai_data.get("font","Default"), ai_data.get("color", "#FFFFFF"), ai_data.get("size", "medium"), 
                    bg_photo=ai_data.get("bg_photo_bytes"), 
                    as_webp=False  # Force PNG for pack
                )
            
            sticker = InputSticker(sticker=BufferedInputFile(png_bytes, "s.png"), format="static", emoji_list=["😀"])
            logger.info(f"Attempting to add sticker to pack {pack_name}")
            await bot.add_sticker_to_set(user_id=uid, name=pack_name, sticker=sticker)
            logger.info(f"Successfully added sticker to pack {pack_name}")
            # Add pack link after sticker addition
            pack_link = f"https://t.me/addstickers/{pack_name}"
            # Clear last_sticker to prepare for next sticker
            if "last_sticker" in s:
                del s["last_sticker"]
            
            # Get current mode to determine next step
            current_mode = s.get("mode", "simple")
            logger.info(f"Current mode after sticker addition: {current_mode}")
            
            if current_mode == "simple":
                # Reset simple mode state for next sticker but keep it initialized
                s.update({"simple": {}, "mode": "simple"})
                await cb.message.answer(
                    f"✅ با موفقیت به پک «{pack_title}» اضافه شد!\n\n"
                    f"🔗 لینک پک: {pack_link}\n\n"
                    f"📝 متنی برای استیکر بعدی بفرستید:", 
                    reply_markup=back_to_menu_kb(uid == ADMIN_ID)
                )
            else:  # AI mode
                # Reset AI mode state for next sticker but keep it initialized
                s.update({"ai": {}, "mode": "ai"})
                await cb.message.answer(
                    f"✅ با موفقیت به پک «{pack_title}» اضافه شد!\n\n"
                    f"🔗 لینک پک: {pack_link}\n\n"
                    f"🎨 برای استیکر بعدی، نوع ایمیج سورس رو انتخاب کنید:", 
                    reply_markup=ai_image_source_kb()
                )
        except Exception as e:
            logger.error(f"Error adding sticker to pack {pack_name}: {type(e).__name__}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await cb.message.answer(f"خطا در افزودن به پک: {e}", reply_markup=back_to_menu_kb(uid == ADMIN_ID))
    elif action == "no":
        s["await_feedback"] = True
        await safe_edit_text(cb, "چه چیزی رو دوست نداشتی؟")
    await cb.answer()

# --- Generic Message Handler ---
@router.message()
async def on_message(message: Message, bot: Bot):
    if not await require_channel_membership(message, bot): return
    uid, is_admin, s = message.from_user.id, message.from_user.id == ADMIN_ID, sess(message.from_user.id)
    pack_wizard = s.get("pack_wizard", {})
    logger.info(f"Message from user {uid}: {message.text[:50] if message.text else 'Non-text message'}, mode: {s.get('mode', 'None')}")

    if pack_wizard.get("step") == "awaiting_name" and message.text:
        pack_name = message.text.strip().lower()
        if any(word in pack_name for word in FORBIDDEN_WORDS) or not is_valid_pack_name(pack_name):
            await message.answer("نام پک نامعتبر یا شامل کلمات غیرمجاز است.", reply_markup=back_to_menu_kb(is_admin)); return

        bot_info = await bot.get_me()
        short_name = f"{pack_name}_by_{bot_info.username}"

        await message.answer("در حال ساخت پک...")
        try:
            dummy_img = render_image("First", "center", "center", "Default", "#FFFFFF", "medium", as_webp=False)
            sticker = InputSticker(sticker=BufferedInputFile(dummy_img, "s.png"), format="static", emoji_list=["🎉"])
            
            try:
                await bot.create_new_sticker_set(uid, short_name, pack_name, stickers=[sticker], sticker_format='static')
            except pydantic_core.ValidationError as e:
                # نادیده گرفتن خطای شناخته شده در نسخه‌های جدید aiogram
                if "result.is_animated" in str(e) and "result.is_video" in str(e):
                    print(f"Ignoring known aiogram validation error for pack {short_name}")
                else:
                    raise e

            add_user_pack(uid, pack_name, short_name)
            mode = pack_wizard.get("mode", "simple")
            s.update({"current_pack_short_name": short_name, "current_pack_title": pack_name, "pack_wizard": {}})
            pack_link = f"https://t.me/addstickers/{short_name}"
            
            if mode == "simple": 
                s.update({"mode": "simple", "simple": {}})
                await message.answer(
                    f"پک استیکر «{pack_name}» با موفقیت ساخته شد!\n\n{pack_link}\n\nحالا متن استیکر را بفرستید.",
                    reply_markup=back_to_menu_kb(is_admin)
                )
            else: 
                s.update({"mode": "ai", "ai": {}})
                await message.answer(
                    f"پک استیکر «{pack_name}» با موفقیت ساخته شد!\n\n{pack_link}\n\nحالا نوع استیکر را انتخاب کنید:",
                    reply_markup=ai_type_kb()
                )
        except TelegramBadRequest as e:
            error_msg = e.message.lower()
            if "invalid sticker set name" in error_msg or "bad request" in error_msg:
                await message.answer(
                    f"نام پک نامعتبر است. خطا: {e.message}\n\n"
                    "لطفاً یک نام دیگر انتخاب کنید که:\n"
                    "• فقط شامل حروف انگلیسی کوچک، عدد و زیرخط باشد\n"
                    "• با حرف شروع شود\n"
                    "• کوتاه‌تر باشد",
                    reply_markup=back_to_menu_kb(is_admin)
                )
            else:
                await message.answer(f"خطا در ساخت پک: {e.message}", reply_markup=back_to_menu_kb(is_admin))
        except Exception as e:
            await message.answer(f"خطای غیرمنتظره: {str(e)}", reply_markup=back_to_menu_kb(is_admin))
        return

    if message.photo:
        s_simple, s_ai = s.get("simple", {}), s.get("ai", {})
        logger.info(f"Photo received in mode: {s.get('mode')}, awaiting_bg_photo - simple: {s_simple.get('awaiting_bg_photo')}, ai: {s_ai.get('awaiting_bg_photo')}")
        
        if s.get("mode") == "simple" and s_simple.get("awaiting_bg_photo"):
            file = await bot.download(message.photo[-1].file_id)
            s_simple["bg_photo_bytes"] = file.read(); s_simple["awaiting_bg_photo"] = False
            img = render_image(s_simple["text"], "center", "center", "Default", "#FFFFFF", "medium", bg_photo=s_simple["bg_photo_bytes"])
            await message.answer_photo(BufferedInputFile(img, "p.png"), caption="پیش‌نمایش:", reply_markup=after_preview_kb("simple"))
        elif s.get("mode") == "ai" and s_ai.get("awaiting_bg_photo"):
            file = await bot.download(message.photo[-1].file_id)
            s_ai["bg_photo_bytes"] = file.read(); s_ai["awaiting_bg_photo"] = False
            await message.answer("عکس دریافت شد. حالا متن را بفرستید:")
        elif s.get("mode") == "ai":
            # In AI mode but not awaiting photo - show helpful message
            await message.answer(
                "عکس دریافت شد! 📸\n\n"
                "برای استفاده از این عکس در استیکر:\n"
                "1. ابتدا نوع استیکر را انتخاب کنید\n"
                "2. سپس منبع تصویر را «عکس» انتخاب کنید\n\n"
                "یا از منو گزینه مورد نظر را انتخاب کنید:",
                reply_markup=ai_image_source_kb()
            )
        elif s.get("mode") == "simple":
            # In simple mode but not awaiting photo - show helpful message
            await message.answer(
                "عکس دریافت شد! 📸\n\n"
                "برای استفاده از این عکس به عنوان پس‌زمینه:\n"
                "1. ابتدا متن استیکر را بفرستید\n"
                "2. سپس گزینه «عکس» را برای پس‌زمینه انتخاب کنید"
            )
        return

    if message.video and s.get("mode") == "ai" and s.get("ai", {}).get("sticker_type") == "video":
        if not is_ffmpeg_installed(): await message.answer("پردازش ویدیو فعال نیست."); return
        await message.answer("در حال پردازش ویدیو...")
        file = await bot.download(message.video.file_id)
        webm_bytes = await process_video_to_webm(file.read())
        if webm_bytes:
            s["last_sticker"] = webm_bytes
            await message.answer_sticker(BufferedInputFile(webm_bytes, "s.webm"))
            await message.answer("از این استیکر راضی بودی؟", reply_markup=rate_kb())
        else: await message.answer("خطا در پردازش ویدیو.")
        return

    if message.text:
        if s.get("await_feedback"):
            s["await_feedback"] = False; await message.answer("ممنون از بازخوردت!", reply_markup=back_to_menu_kb(is_admin))
        # Check if user has an active pack and can add stickers directly
        elif s.get("current_pack_short_name") and s.get("current_pack_title"):
            logger.info(f"User {uid} has active pack {s.get('current_pack_short_name')} - creating sticker directly")
            current_mode = s.get("mode", "simple")
            if current_mode == "simple":
                s["simple"]["text"] = message.text.strip()
                await message.answer("پس\u200cزمینه را انتخاب کنید:", reply_markup=simple_bg_kb())
        elif s.get("mode") == "simple":
            s["simple"]["text"] = message.text.strip()
            await message.answer("پس‌زمینه را انتخاب کنید:", reply_markup=simple_bg_kb())
        elif s.get("mode") == "ai":
            s["ai"]["text"] = message.text.strip()
            await message.answer("موقعیت عمودی متن:", reply_markup=ai_vpos_kb())
        return

    await message.answer("دستور شما مشخص نیست.", reply_markup=main_menu_kb(is_admin))
