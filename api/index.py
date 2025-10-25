import os
import sys
import logging
import asyncio
from fastapi import Request, FastAPI, Response, status
import telebot
from telebot.types import Update

# --- تنظیمات لاگ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- تنظیمات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN not found in environment variables!")
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

# --- ساخت نمونه ربات ---
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# --- اضافه کردن مسیر ریشه پروژه ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- ایمپورت و ثبت هندلر ---
try:
    import handlers
    handlers.register_handlers(bot)
    print("INFO: Handlers registered successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to import or register handlers: {e}")
    import traceback
    traceback.print_exc()
    raise

# --- اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    """
    این نقطه پایانی، درخواست‌های وب‌هوک تلگرام را دریافت کرده و با استفاده از
    asyncio.to_thread به صورت غیرهمزمان به ربات تحویل می‌دهد.
    """
    try:
        data = await request.json()
        update = Update.de_json(data)
        
        print(f"DEBUG: Received update: {update}") # لاگ برای دیدن آپدیت دریافتی
        
        # --- این بخش کلیدی و جدید است ---
        # استفاده از asyncio.to_thread برای اجرای کد همزمان
        await asyncio.to_thread(bot.process_new_updates, [update])
        # -------------------------
        
        print("DEBUG: bot.process_new_updates finished.")
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Exception in webhook handler: {e}")
        import traceback
        traceback.print_exc() # چاپ کامل خطا برای دیباگ
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running with asyncio.to_thread"}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    logging.warning(f"Received request for unknown path: {request.method} /{path}")
    return Response(
        content=f"This endpoint is not available. Please use /webhook for Telegram bot requests.",
        status_code=status.HTTP_404_NOT_FOUND
    )
