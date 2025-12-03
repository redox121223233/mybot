"""
Main entry point for running the bot locally
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot_core.config import BOT_TOKEN
from bot_core.bot_logic import router

async def main():
    """Main function to run the bot"""
    global BOT_USERNAME

    # Create bot and dispatcher
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Include all handlers
    dp.include_router(router)
    
    # Get bot info
    bot_info = await bot.get_me()
    BOT_USERNAME = bot_info.username
    print(f"ربات با نام کاربری @{BOT_USERNAME} شروع به کار کرد")

    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
