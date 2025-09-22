# utils/telegram_api.py
import requests
import logging
from config import BOT_TOKEN, CHANNEL_USERNAME

logger = logging.getLogger(__name__)

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

class TelegramAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    def request(self, method: str, params=None, files=None):
        url = f"{self.base_url}/{method}"
        response = requests.post(url, params=params, files=files)
        if response.status_code != 200:
            raise Exception(f"❌ خطای HTTP {response.status_code}: {response.text}")
        return response.json()

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        resp = self.request("sendMessage", params=payload)
        logger.info(f"send_message: {resp}")
        return resp

    # ------------------ عضویت اجباری ------------------
    def check_channel_membership(self, user_id: int) -> bool:
        try:
            channel_username = CHANNEL_USERNAME.replace("@", "")
            logger.info(f"🔍 Checking membership: chat_id=@{channel_username}, user_id={user_id}")

            resp = requests.get(API + "getChatMember", params={
                "chat_id": f"@{channel_username}",
                "user_id": user_id
            }).json()

            if resp.get("ok"):
                status = resp["result"]["status"]
                return status in ["member", "administrator", "creator"]
            else:
                logger.error(f"❌ Error checking membership: {resp}")
                return False
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False

    def send_membership_required_message(self, chat_id: int):
        """ارسال پیام عضویت اجباری"""
        message = f"""🔒 برای استفاده از ربات باید در کانال عضو شوید:

📢 {CHANNEL_USERNAME}

بعد از عضویت، دوباره /start را بزنید ✅"""

        keyboard = {
            "inline_keyboard": [[
                {"text": "📢 عضویت در کانال", "url": f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"}
            ]]
        }

        return self.send_message(chat_id, message, reply_markup=keyboard)
