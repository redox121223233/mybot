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
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# --- اضافه کردن مسیر ریشه پروژه ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- ایمپورت و ثبت هندلر ---
try:
    import handlers
    handlers.register_handlers(bot)
    print("DEBUG: Handlers registered successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to import or register handlers: {e}")
    raise

# --- اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    print("DEBUG: Webhook endpoint hit.")
    try:
        data = await request.json()
        print(f"DEBUG: Received JSON data: {data}")
        
        update = Update.de_json(data)
        print(f"DEBUG: Parsed update: {update}")
        
        bot.process_new_updates([update])
        print("DEBUG: bot.process_new_updates finished.")
        
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        print(f"ERROR: Exception in webhook handler: {e}")
        import traceback
        traceback.print_exc() # این خط کاملترین جزئیات خطا را چاپ می‌کند
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running in minimal mode"}
