import os
import sys
import logging
import asyncio # برای اجرای کد همزمان در زمینه جداگانه
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
        # خواندن داده‌های JSON از بدنه درخواست
        data = await request.json()
        
        # تبدیل داده‌ها به یک آبجکت آپدیت تلگرام
        update = Update.de_json(data)
        
        # --- این بخش کلیدی است ---
        # پردازش آپدیت را در یک زمینه جداگانه (thread) اجرا می‌کنیم
        # تا از قفل شدن حلقه رویداد FastAPI جلوگیری شود.
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, bot.process_new_updates, [update])
        # -------------------------
        
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        logging.error(f"ERROR: Exception in webhook handler: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running with async/sync separation"}
