import os
import logging
from fastapi import Request, FastAPI, Response, status
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Update

# --- تنظیمات لاگ برای دیدن همه چیز ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- تنظیمات ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("BOT_TOKEN not found in environment variables!")
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# --- هندلرها ---
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    logging.info(f"Received /start from user {message.from_user.id}")
    await message.answer("سلام! ربات با موفقیت روی Vercel اجرا شد. ✅")

@dp.message()
async def echo_message(message: types.Message):
    logging.info(f"Received message: {message.text}")
    await message.answer(f"پیام شما: {message.text}")

# --- اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    logging.info("Webhook received a request!")
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(update=update, bot=bot)
        return Response(content="OK", status_code=status.HTTP_200_OK)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/")
async def read_root():
    return {"status": "Bot is running on Vercel"}
