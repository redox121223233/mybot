# --- handlers.py (نسخه حداقلی برای عیب‌یابی) ---
import telebot
from telebot import types

def register_handlers(bot: telebot.TeleBot):
    """
    این تابع فقط یک هندلر ساده را ثبت می‌کند.
    """
    @bot.message_handler(commands=['start'])
    def start_command(message: types.Message):
        print(f"DEBUG: Received /start from user {message.from_user.id}") # این لاگ در Vercel Functions ظاهر می‌شود
        bot.reply_to(message, "✅ ربات در حالت حداقلی کار می‌کند! مشکل از کدهای پیچیده‌تر است.")
