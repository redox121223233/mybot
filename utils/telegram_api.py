import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    def request(self, method: str, params: dict = None, files: dict = None):
        url = f"{self.base_url}/{method}"
        resp = requests.post(url, data=params, files=files)
        if resp.status_code != 200:
            raise Exception(f"❌ خطای HTTP {resp.status_code}: {resp.text}")
        return resp.json()

    def send_message(self, chat_id, text, reply_markup=None):
        params = {"chat_id": chat_id, "text": text}
        if reply_markup:
            params["reply_markup"] = reply_markup
        resp = self.request("sendMessage", params=params)
        logger.info(f"send_message: {resp}")
        return resp

    def is_user_in_channel(self, user_id, channel_id):
        """ بررسی اینکه آیا کاربر عضو کانال هست یا نه """
        try:
            chat_id = channel_id if isinstance(channel_id, str) and channel_id.startswith("@") else int(channel_id)
            resp = self.request("getChatMember", {
                "chat_id": chat_id,
                "user_id": user_id
            })
            status = resp.get("result", {}).get("status")
            return status in ["member", "administrator", "creator"]
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False

    def set_webhook(self, url: str):
        """ ست کردن وبهوک روی دامنه """
        try:
            resp = self.request("setWebhook", params={"url": url})
            logger.info(f"✅ Webhook response: {resp}")
            return resp
        except Exception as e:
            logger.error(f"❌ خطا در setWebhook: {e}")
            raise
