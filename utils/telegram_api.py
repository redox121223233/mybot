import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_url = f"https://api.telegram.org/file/bot{token}"
        self.username = None  # بعدا از getMe پر میشه

    def get_me(self):
        """دریافت اطلاعات ربات"""
        url = f"{self.base_url}/getMe"
        response = requests.get(url).json()
        if response.get("ok"):
            self.username = response["result"]["username"]
        return response

    def send_message(self, chat_id, text, reply_markup=None):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
        }
        response = requests.post(url, json=payload)
        logger.info(f"send_message: {response.text}")
        return response.json()

    def send_sticker(self, chat_id, sticker_path):
        """ارسال استیکر به کاربر"""
        url = f"{self.base_url}/sendSticker"
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            data = {"chat_id": chat_id}
            response = requests.post(url, data=data, files=files)
        logger.info(f"send_sticker: {response.text}")
        return response.json()

    def download_file(self, file_id, dest_path):
        """دانلود فایل از تلگرام"""
        url = f"{self.base_url}/getFile"
        response = requests.get(url, params={"file_id": file_id}).json()
        if not response.get("ok"):
            raise Exception(f"خطا در گرفتن فایل: {response}")
        file_path = response["result"]["file_path"]
        file_url = f"{self.file_url}/{file_path}"
        r = requests.get(file_url)
        with open(dest_path, "wb") as f:
            f.write(r.content)
        logger.info(f"📥 File downloaded: {dest_path}")
        return dest_path

    def set_webhook(self, url: str):
        """تنظیم وبهوک روی تلگرام"""
        endpoint = f"{self.base_url}/setWebhook"
        payload = {"url": url}
        response = requests.post(endpoint, data=payload)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"خطا در setWebhook: {response.text}")
