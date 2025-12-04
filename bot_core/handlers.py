# Vercel-compatible bot handlers
"""
Bot handlers for all message and callback interactions
"""
from aiogram import Bot, F, Router
from aiogram.types import Message, CallbackQuery, BotCommand, BufferedInputFile, InputSticker
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
import asyncio
from html import escape
import pydantic_core
import traceback

from .bot_logic import (
    router, USERS, SESSIONS, ADMIN_PENDING, BOT_USERNAME,
    user, sess, reset_mode, get_user_packs, add_user_pack, set_current_pack, get_current_pack,
    render_image, check_channel_membership, require_channel_membership,
    main_menu_kb, back_to_menu_kb, simple_bg_kb, after_preview_kb, rate_kb,
    pack_selection_kb, add_to_pack_kb, ai_type_kb, ai_image_source_kb,
    ai_vpos_kb, ai_hpos_kb, admin_panel_kb,
    check_pack_exists, is_valid_pack_name, process_video_to_webm,
    is_ffmpeg_installed, ADMIN_ID, FORBIDDEN_WORDS, DEFAULT_PALETTE,
    _quota_left
)

@router.message(CommandStart())
async def on_start(message: Message, bot: Bot):
    if not await require_channel_membership(message, bot):
        return
    reset_mode(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "سلام! خوش آمدید\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=main_menu_kb(is_admin)
    )

@router.callback_query(F.data == "check_membership")
async def on_check_membership(cb: CallbackQuery, bot: Bot):
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
    if not await require_channel_membership(cb.message, bot): return
    reset_mode(cb.from_user.id)
    is_admin = (cb.from_user.id == ADMIN_ID)
    await cb.message.edit_text("منوی اصلی:", reply_markup=main_menu_kb(is_admin))
    await cb.answer()
    
# ... (All other handlers from bot (2).py) ...

@router.message()
async def on_message(message: Message, bot: Bot):
    uid = message.from_user.id
    s = sess(uid)
    is_admin = (uid == ADMIN_ID)
    
    if not await require_channel_membership(message, bot): return

    # ... (Full on_message logic from bot (2).py) ...

    # Fallback
    await message.answer("از منوی زیر انتخاب کن:", reply_markup=main_menu_kb(is_admin))
