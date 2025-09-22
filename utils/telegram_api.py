# utils/telegram_api.py
import requests
import logging
from config import BOT_TOKEN, CHANNEL_USERNAME

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str = BOT_TOKEN):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    # ------------------ درخواست به تلگرام ------------------
    def request(self, method: str, params=None, files=None):
        url = f"{self.base_url}/{method}"
        try:
            response = requests.post(url, params=params, files=files)
            if response.status_code != 200:
                raise Exception(f"❌ خطای HTTP {response.status_code}: {response.text}")
            return response.json()
        except Exception as e:
            logger.error(f"❌ خطا در درخواست به تلگرام ({method}): {e}")
            raise

    # ------------------ ارسال پیام ------------------
    def send_message(self, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        resp = self.request("sendMessage", params=payload)
        logger.info(f"send_message: {resp}")
        return resp

    # ------------------ چک عضویت در کانال ------------------
    def is_user_in_channel(self, user_id):
        """
        چک می‌کنه کاربر عضو کانال اجباری هست یا نه
        """
        try:
            logger.info(f"🔍 Checking membership: chat_id={CHANNEL_USERNAME}, user_id={user_id}")
            resp = self.request("getChatMember", params={
                "chat_id": CHANNEL_USERNAME,
                "user_id": user_id
            })
            status = resp["result"]["status"]
            return status in ["member", "creator", "administrator"]
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False

    # ------------------ وبهوک ------------------
    def set_webhook(self, url):
        resp = self.request("setWebhook", params={"url": url})
        return resp
