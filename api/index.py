import os
import re
from io import BytesIO
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import subprocess
import pydantic_core
import traceback

from fastapi import Request, FastAPI
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, BotCommand, BufferedInputFile, InputSticker, Update
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.strategy import FSMStrategy

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import arabic_reshaper
from bidi.algorithm import get_display

# =============== پیکربندی ===============
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN را در تنظیمات Vercel قرار دهید.")

CHANNEL_USERNAME = "@redoxbot_sticker"
SUPPORT_USERNAME = "@onedaytoalive"
ADMIN_ID = 6053579919

# ... (تمام توابع کمکی شما را اینجا کپی کنید) ...
# من برای صرفه‌جویی، آن‌ها را اینجا نمی‌نویسم. شما باید آن‌ها را کپی کنید.
# _today_start_ts, user, sess, render_image, main_menu_kb و غیره...

# یک نمونه از توابع برای مثال
def user(uid: int) -> Dict[str, Any]:
    if uid not in USERS:
        USERS[uid] = {
            "ai_used": 0, "vote": None, "day_start": _today_start_ts(), "packs": [], "current_pack": None
        }
    _reset_daily_if_needed(USERS[uid])
    return USERS[uid]

# ... (بقیه توابع کمکی و هندلرهای خود را اینجا کپی کنید) ...
# @router.message(CommandStart())
# async def on_start(...): ...
# @router.callback_query(F.data == "menu:home")
# async def on_home(...): ...


# =============== بخش اصلی وب‌هوک (اصلاح شده) ===============
storage = MemoryStorage()
dp = Dispatcher(storage=storage, fsm_strategy=FSMStrategy.CHAT)
dp.include_router(router)

# یک نمونه از بوت را در سطح بالا بسازید
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

app = FastAPI()

@app.post("/webhook")
async def bot_webhook(request: Request):
    print("Webhook received a request!") # لاگ برای دیباگ
    try:
        update_data = await request.json()
        update = Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_webhook_update(update, bot=bot)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get("/")
async def read_root():
    return {"status": "Bot is running"}
