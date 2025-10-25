import os
import sys
import logging
import asyncio
import json # برای لاگ گرفتن از بدنه خام
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
    لاگ‌گیری دقیق، مشکل را پیدا می‌کند.
    """
    try:
        # --- لاگ گرفتن از بدنه خام درخواست ---
        body = await request.body()
        print(f"DEBUG: Raw request body received: {body}")
        
        # اگر بدنه خالی بود، این یک مشکل است
        if not body:
            print("ERROR: Request body is empty!")
            return Response(content="Bad Request: Empty body", status_code=status.HTTP_400_BAD_REQUEST)
        
        # تلاش برای تبدیل بدنه به JSON
        try:
            data = await request.json()
            print(f"DEBUG: Parsed JSON data: {data}")
        except Exception as e:
            print(f"ERROR: Failed to parse JSON: {e}")
            return Response(content="Bad Request: Invalid JSON", status_code=status.HTTP_400_BAD_REQUEST)
        
        # تلاش برای ساخت آبجکت آپدیت
        try:
            update = Update.de_json(data)
            print(f"DEBUG: Parsed Update object: {update}")
        except Exception as e:
            print(f"ERROR: Failed to create Update object: {e}")
            return Response(content="Bad Request: Invalid Update object", status_code=status.HTTP_400_BAD_REQUEST)
        
        # اگر همه چیز تا اینجا درست بود، ربات را اجرا کن
        print("DEBUG: All checks passed. Processing update...")
        await asyncio.to_thread(bot.process_new_updates, [update])
        print("DEBUG: bot.process_new_updates finished.")
        
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Unhandled exception in webhook handler: {e}")
        import traceback
        traceback.print_exc()
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running with detailed logging"}

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    logging.warning(f"Received request for unknown path: {request.method} /{path}")
    return Response(
        content=f"This endpoint is not available. Please use /webhook for Telegram bot requests.",
        status_code=status.HTTP_404_NOT_FOUND
    )
