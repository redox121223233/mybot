import requests
import logging
import os

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

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

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        resp = self.request("sendMessage", params=payload)
        logger.info(f"send_message: {resp}")
        return resp

    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            resp = self.request("sendSticker", params={"chat_id": chat_id}, files=files)
            logger.info(f"send_sticker: {resp}")
            return resp

    def download_file(self, file_id, dest_path):
        resp = self.request("getFile", params={"file_id": file_id})
        file_path = resp["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        r = requests.get(file_url)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            logger.info(f"📥 File downloaded: {dest_path}")
        else:
            raise Exception(f"خطا در دانلود فایل: {r.text}")

    def set_webhook(self, url):
        resp = self.request("setWebhook", params={"url": url})
        return resp

    def is_user_in_channel(self, channel_username, user_id):
        try:
            if channel_username.startswith("@"):
                channel_username = channel_username[1:]
            resp = self.request("getChatMember", params={
                "chat_id": f"@{channel_username}",
                "user_id": user_id
            })
            status = resp["result"]["status"]
            return status in ["member", "creator", "administrator"]
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False
