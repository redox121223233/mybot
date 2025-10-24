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
    این نقطه پایانی، درخواست‌های وب‌هوک تلگرام را دریافت کرده و به صورت غیرهمزمان
    به ربات تحویل می‌دهد تا از تداخل با حلقه رویداد FastAPI جلوگیری شود.
    """
    try:
        data = await request.json()
        update = Update.de_json(data)
        
        # اجرای کد همزمان ربات در یک زمینه جداگانه
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, bot.process_new_updates, [update])
        
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        logging.error(f"ERROR: Exception in webhook handler: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    """
    این مسیر برای بررسی سلامت ربات است و از خطای 404 جلوگیری می‌کند.
    """
    return {"status": "Bot is running with async/sync separation and no 404s"}

# --- این بخش جدید برای جلوگیری از هرگونه خطای 404 است ---
@app.middleware("http")
async def add_no_cache_header(request: Request, call_next):
    """
    این میدل‌ور هدرهای Cache-Control را اضافه می‌کند تا از مشکلات احتمالی کش جلوگیری شود.
    """
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    """
    این مسیر تمام درخواست‌هایی که به مسیرهای دیگر (مانند /webhook) تعلق ندارند
    را مدیریت می‌کند و از خطای 404 جلوگیری می‌کند.
    """
    logging.warning(f"Received request for unknown path: {request.method} /{path}")
    return Response(
        content=f"This endpoint is not available. Please use /webhook for Telegram bot requests.",
        status_code=status.HTTP_404_NOT_FOUND
    )
