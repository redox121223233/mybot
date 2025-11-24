"""
Start command handler
"""
from aiogram import Bot, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from .bot_logic import router, require_channel_membership, main_menu_kb, ADMIN_ID, reset_mode
from .handlers import on_message  # Import message handler

@router.message(CommandStart())
async def on_start(message: Message, bot: Bot):
    if not await require_channel_membership(message, bot):
        return
        
    reset_mode(message.from_user.id)
    is_admin = (message.from_user.id == ADMIN_ID)
    await message.answer(
        "سلام! خوش آمدی\n"
        "یکی از گزینه‌های زیر را انتخاب کن:",
        reply_markup=main_menu_kb(is_admin)
    )