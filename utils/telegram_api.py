import requests
import logging
import json

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
            params["reply_markup"] = json.dumps(reply_markup)  # ✅ تبدیل به JSON
        resp = self.request("sendMessage", params=params)
        logger.info(f"send_message: {resp}")
        return resp

    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            params = {"chat_id": chat_id}
            resp = self.request("sendSticker", params=params, files=files)
            logger.info(f"send_sticker: {resp}")
            return resp

    def download_file(self, file_id, dest_path):
        file_info = self.request("getFile", params={"file_id": file_id})
        file_path = file_info["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        resp = requests.get(url)
        if resp.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"📥 File downloaded: {dest_path}")
            return dest_path
        else:
            raise Exception(f"❌ خطا در دانلود فایل: {resp.text}")

    def set_webhook(self, url: str):
        """تنظیم وبهوک"""
        params = {"url": url}
        resp = self.request("setWebhook", params=params)
        return resp

    def is_user_in_channel(self, channel_username: str, user_id: int) -> bool:
        """بررسی عضویت کاربر در کانال"""
        try:
            resp = self.request("getChatMember", params={
                "chat_id": channel_username,
                "user_id": user_id
            })
            status = resp["result"]["status"]
            return status in ["member", "administrator", "creator"]
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False
