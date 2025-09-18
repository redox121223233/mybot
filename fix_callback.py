import os
import logging
import requests
import json

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fix_callback")

# تنظیمات ربات
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    BOT_TOKEN = input("لطفاً توکن ربات را وارد کنید: ")

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

def answer_callback_query(query_id, text=None, show_alert=False):
    """پاسخ به کالبک کوئری - اصلاح شده"""
    try:
        data = {"callback_query_id": query_id}
        if text:
            data["text"] = text
        if show_alert:
            data["show_alert"] = show_alert
            
        # ارسال درخواست به API تلگرام
        response = requests.post(f"{API}answerCallbackQuery", json=data)
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"Callback query answered: {query_id}")
            return True
        else:
            logger.error(f"Error answering callback query: {result}")
            return False
    except Exception as e:
        logger.error(f"Exception in answer_callback_query: {e}")
        return False

def main():
    """تست تابع اصلاح شده"""
    print("این اسکریپت برای اصلاح مشکل دکمه‌های اینلاین در ربات استیکر است.")
    print("برای استفاده از این اصلاح، کد تابع answer_callback_query را در فایل bot.py جایگزین کنید.")
    print("\nکد اصلاح شده:")
    print("""
def answer_callback_query(query_id, text=None, show_alert=False):
    \"\"\"پاسخ به کالبک کوئری\"\"\"
    try:
        data = {"callback_query_id": query_id}
        if text:
            data["text"] = text
        if show_alert:
            data["show_alert"] = show_alert
            
        # ارسال درخواست به API تلگرام
        response = requests.post(f"{API}answerCallbackQuery", json=data)
        result = response.json()
        
        if result.get("ok"):
            return True
        else:
            logger.error(f"Error answering callback query: {result}")
            return False
    except Exception as e:
        logger.error(f"Exception in answer_callback_query: {e}")
        return False
    """)

if __name__ == "__main__":
    main()