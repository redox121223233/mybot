import os
import sys
import logging
import traceback
from fastapi import Request, FastAPI, Response, status
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- تنظیمات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN not found in environment variables!")
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

# --- اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    """
    این تابع برای هر درخواست، یک نمونه جدید از ربات و دیسپچر می‌سازد
    تا از مشکلات حالت (state) در محیط Serverless جلوگیری کند.
    """
    try:
        data = await request.json()
        
        # ساخت نمونه جدید از بات با استفاده از DefaultBotProperties
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        
        # ساخت نمونه جدید از دیسپچر و پاس دادن نمونه بات به آن
        dp = Dispatcher(bot=bot)

        # ایمپورت و ثبت هندلرها
        import handlers
        handlers.register_handlers(dp)

        # ساخت آبجکت آپدیت و پردازش آن
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(update=update, bot=bot)
        
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running on Vercel with aiogram (stateless, v3.7+)"}
