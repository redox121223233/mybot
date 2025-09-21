import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    # ارسال درخواست عمومی
    def request(self, method, params=None, files=None):
        url = f"{self.base_url}/{method}"
        resp = requests.post(url, params=params, files=files)

        if resp.status_code != 200:
            raise Exception(f"❌ خطای HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        if not data.get("ok"):
            raise Exception(f"❌ خطا در درخواست به تلگرام ({method}): {resp.text}")

        return data

    # 📌 تنظیم وبهوک
    def set_webhook(self, url):
        return self.request("setWebhook", params={"url": url})

    # ارسال پیام
    def send_message(self, chat_id, text, reply_markup=None):
        params = {"chat_id": chat_id, "text": text}
        if reply_markup:
            params["reply_markup"] = reply_markup
        return self.request("sendMessage", params=params)

    # ارسال استیکر
    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            return self.request("sendSticker", params={"chat_id": chat_id}, files={"sticker": f})

    # دانلود فایل
    def download_file(self, file_id, save_path):
        file_info = self.request("getFile", params={"file_id": file_id})
        file_path = file_info["result"]["file_path"]

        file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        resp = requests.get(file_url)

        if resp.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"📥 File downloaded: {save_path}")
            return save_path
        else:
            raise Exception(f"خطا در دانلود فایل: {resp.text}")
