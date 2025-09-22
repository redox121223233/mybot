import requests
import logging

from config import BOT_TOKEN

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str = BOT_TOKEN):
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
        return self.request("sendMessage", params=payload)

    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            return self.request("sendSticker", params={"chat_id": chat_id}, files=files)

    def download_file(self, file_id, dest_path):
        resp = self.request("getFile", params={"file_id": file_id})
        file_path = resp["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"

        r = requests.get(file_url)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            logger.info(f"📥 File downloaded: {dest_path}")
            return dest_path
        else:
            raise Exception(f"خطا در دانلود فایل: {r.text}")

    def get_me(self):
        return self.request("getMe")

    def get_chat_member(self, chat_id, user_id):
        return self.request("getChatMember", params={"chat_id": chat_id, "user_id": user_id})

    def set_webhook(self, url):
        return self.request("setWebhook", params={"url": url})
