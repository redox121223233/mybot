import os
import asyncio
from fastapi import Request, FastAPI, Response
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Update

# --- تنظیمات ---
# توکن ربات خود را از تنظیمات Vercel می‌خواند
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

# --- ایجاد نمونه‌های بوت و دیسپچر ---
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# --- تعریف هندلرها ---
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.answer(
        f"سلام {message.from_user.full_name}! 👋\n"
        f"این یک ربات تست است که روی Vercel میزبانی می‌شود.\n"
        f"وضعیت: ✅ موفق و در حال کار!",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="چک کردن وضعیت", callback_data="check_status")]
            ]
        )
    )

@dp.callback_query(lambda c: c.data == "check_status")
async def show_status(call: types.CallbackQuery):
    await call.message.edit_text("وضعیت ربات: ✅ عالی است!")
    await call.answer("بررسی شد!")


# --- ایجاد اپلیکیشن FastAPI ---
app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    # لاگ برای اینکه بفهمیم درخواست می‌رسد
    print("Webhook received a request!")

    try:
        # خواندن داده‌های JSON از درخواست تلگرام
        data = await request.json()
        
        # ساختن آبجکت Update از داده‌ها
        update = Update.model_validate(data, context={"bot": bot})
        
        # ارسال آپدیت به دیسپچر برای پردازش
        await dp.feed_update(update=update, bot=bot)
        
        return Response(content="OK", status_code=200)

    except Exception as e:
        # چاپ خطا برای دیباگ
        print(f"Error processing update: {e}")
        return Response(content="Internal Server Error", status_code=500)


@app.get("/")
async def read_root():
    return {"status": "Bot is running on Vercel"}
