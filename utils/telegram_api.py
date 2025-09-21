import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def request(self, method: str, params=None, files=None):
        url = f"{self.base_url}/{method}"
        try:
            response = requests.post(url, data=params, files=files)
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
        return self.request("sendMessage", params=payload)

    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            return self.request("sendSticker", params={"chat_id": chat_id}, files=files)

    def download_file(self, file_id, save_path):
        file_info = self.request("getFile", params={"file_id": file_id})
        if not file_info.get("ok"):
            raise Exception(f"خطا در گرفتن فایل: {file_info}")
        file_path = file_info["result"]["file_path"]

        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        r = requests.get(url)
        if r.status_code != 200:
            raise Exception(f"خطا در دانلود فایل: {r.text}")

        with open(save_path, "wb") as f:
            f.write(r.content)
        logger.info(f"📥 File downloaded: {save_path}")
        return save_path

    def set_webhook(self, url: str):
        """تنظیم وبهوک"""
        logger.info(f"🌍 Setting webhook to {url}")
        resp = self.request("setWebhook", params={"url": url})
        return resp
