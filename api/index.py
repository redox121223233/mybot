import os
import sys
import logging
import traceback
from fastapi import Request, FastAPI, Response, status

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
    این تابع با لاگ‌گیری کامل، مشکل را پیدا می‌کند.
    """
    print("--- Webhook Request Started ---")
    try:
        data = await request.json()
        print(f"Step 1: JSON data received successfully.")
        
        # تست وارد کردن ماژول‌های aiogram
        try:
            from aiogram import Bot, Dispatcher, types, ParseMode
            from aiogram.types import Update
            print("Step 2: aiogram modules imported successfully.")
        except ImportError as e:
            print(f"CRITICAL ERROR: Failed to import aiogram modules: {e}")
            traceback.print_exc()
            return Response(content="Internal Server Error: Import failed", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ساخت نمونه جدید از بات
        bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
        print("Step 3: Bot instance created.")
        
        # ساخت نمونه جدید از دیسپچر
        dp = Dispatcher(bot=bot)
        print("Step 4: Dispatcher instance created. This line should not cause an error.")
        
        # ایمپورت و ثبت هندلرها
        try:
            import handlers
            handlers.register_handlers(dp)
            print("Step 5: Handlers registered successfully.")
        except Exception as e:
            print(f"ERROR: Failed to register handlers: {e}")
            traceback.print_exc()
            return Response(content="Internal Server Error: Handler registration failed", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # ساخت آبجکت آپدیت و پردازش آن
        update = Update.model_validate(data, context={"bot": bot})
        print("Step 6: Update object created.")
        
        await dp.feed_update(update=update, bot=bot)
        print("Step 7: Update processed successfully.")
        
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Unhandled exception in webhook: {e}")
        traceback.print_exc() # این خط کلیدی است. تمام جزئیات خطا را چاپ می‌کند.
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running in detailed debug mode"}
