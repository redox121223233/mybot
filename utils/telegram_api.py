import requests
import logging
from config import BOT_TOKEN

class TelegramAPI:
    def __init__(self, token=BOT_TOKEN):
        self.base_url = f"https://api.telegram.org/bot{token}"

    def request(self, method, params=None):
        url = f"{self.base_url}/{method}"
        response = requests.post(url, json=params)
        if not response.ok:
            raise Exception(f"❌ خطای HTTP {response.status_code}: {response.text}")
        return response.json()

    def send_message(self, chat_id, text, reply_markup=None):
        params = {
            "chat_id": chat_id,
            "text": text
        }
        if reply_markup:
            params["reply_markup"] = reply_markup
        logging.info(f"send_message: {params}")
        return self.request("sendMessage", params=params)

    def is_user_in_channel(self, user_id, channel_username):
        try:
            params = {"chat_id": channel_username, "user_id": int(user_id)}
            response = self.request("getChatMember", params=params)
            status = response["result"]["status"]
            return status in ["member", "administrator", "creator"]
        except Exception as e:
            logging.error(f"❌ خطا در بررسی عضویت: {e}")
            return False
