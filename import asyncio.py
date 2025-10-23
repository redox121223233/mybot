import asyncio
from aiogram import Bot

# توکن جدید خود را اینجا قرار دهید
BOT_TOKEN = "8324626018:AAFgs64L9E4-nfqLyNDTJmrYumoX3keTbUQ"

async def main():
    print("در حال اتصال به تلگرام...")
    try:
        bot = Bot(token=BOT_TOKEN)
        bot_info = await bot.get_me()
        print(f"✅ موفقیت! ربات شما با نام کاربری @{bot_info.username} با موفقیت متصل شد.")
        print("اطلاعات کامل ربات:", bot_info)
    except Exception as e:
        print(f"❌ خطا در اتصال به ربات: {e}")

if __name__ == "__main__":
    asyncio.run(main())