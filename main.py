import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Import our refactored modules
from bot_core.handlers import *
from bot_core.bot_logic import router

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    """Main function for the bot using refactored structure"""
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    # Include the router from our refactored modules
    dp.include_router(router)
    
    try:
        print("Bot is starting...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())