import os
import json
import logging
from fastapi import Request, FastAPI, Response, status
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Update

# --- تنظیمات لاگ برای دیدن همه چیز ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- تنظیمات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN not found in environment variables!")
    # We'll let it crash so Vercel shows an error in the log
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# --- هندلرها ---
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    logging.info(f"Received /start from user {message.from_user.id}")
    await message.answer("سلام! ربات تشخیصی فعال است. هر پیامی بفرستی دوباره برایت می‌فرستم.")

@dp.message()
async def echo_message(message: types.Message):
    logging.info(f"Received message from user {message.from_user.id}: {message.text}")
    await message.answer(f"پیام شما دریافت شد: {message.text}")

# --- اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    logging.info("Webhook received a request!") # این لاگ مهم است
    
    try:
        # لاگ کردن داده‌های خام برای دیباگ
        body = await request.body()
        logging.info(f"Raw body: {body.decode('utf-8')}")
        
        data = await request.json()
        logging.info(f"JSON data: {json.dumps(data, indent=2)}")
        
        update = Update.model_validate(data, context={"bot": bot})
        logging.info(f"Successfully created Update object: {update}")
        
        await dp.feed_update(update=update, bot=bot)
        logging.info("Update fed to dispatcher successfully.")
        
        return Response(content="OK", status_code=status.HTTP_200_OK)

    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running on Vercel"}
