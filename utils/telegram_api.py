import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, chat_id, text, reply_markup=None):
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(url, json=payload)
        logger.info(f"send_message: {response.text}")
        return response.json()

    def download_file(self, file_id, save_path):
        file_info = requests.get(f"{self.base_url}/getFile?file_id={file_id}").json()
        if not file_info.get("ok"):
            raise Exception(f"خطا در گرفتن اطلاعات فایل: {file_info}")
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        response = requests.get(file_url)
        with open(save_path, "wb") as f:
            f.write(response.content)
        logger.info(f"📥 File downloaded: {save_path}")

    def set_webhook(self, url):
        webhook_url = f"{self.base_url}/setWebhook"
        payload = {"url": url}
        response = requests.post(webhook_url, json=payload)
        logger.info(f"set_webhook: {response.text}")
        return response.json()
