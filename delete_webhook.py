#!/usr/bin/env python3
import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

async def delete_webhook():
    if not BOT_TOKEN:
        print("BOT_TOKEN not found!")
        return

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    try:
        result = await bot.delete_webhook(drop_pending_updates=True)
        print(f"Webhook deleted successfully: {result}")

        # Check webhook info
        info = await bot.get_webhook_info()
        print(f"Current webhook info: {info}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(delete_webhook())
