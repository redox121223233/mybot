import os
import sys
import logging
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
# از این نمونه برای تمام هندلرها استفاده خواهیم کرد
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# --- اضافه کردن مسیر ریشه پروژه برای پیدا کردن فایل هندلر ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- ایمپورت و ثبت تمام هندلرها ---
# تمام منطق ربات در فایل handlers.py قرار دارد
import handlers
handlers.register_handlers(bot)

# --- اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    """
    این نقطه پایانی، درخواست‌های وب‌هوک تلگرام را دریافت کرده و به ربات تحویل می‌دهد.
    """
    try:
        # خواندن داده‌های JSON از بدنه درخواست
        data = await request.json()
        
        # تبدیل داده‌ها به یک آبجکت آپدیت تلگرام
        update = Update.de_json(data)
        
        # پردازش آپدیت توسط ربات
        bot.process_new_updates([update])
        
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running on Vercel with pyTelegramBotAPI"}
