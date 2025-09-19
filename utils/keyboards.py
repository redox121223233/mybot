import requests
import os

TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(f"{API_URL}/sendMessage", json=data, timeout=5)
    except Exception as e:
        print("send_message error:", e)

def main_menu(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "🎁 تست رایگان"}, {"text": "⭐ اشتراک"}],
            [{"text": "🎭 استیکرساز"}]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "به منوی اصلی خوش آمدید 🌟", reply_markup=keyboard)
