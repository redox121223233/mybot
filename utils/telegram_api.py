import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    def request(self, method, params=None, files=None):
        url = f"{self.base_url}/{method}"
        response = requests.post(url, params=params, files=files)
        if not response.ok:
            raise Exception(f"❌ خطای HTTP {response.status_code}: {response.text}")
        return response.json()

    def send_message(self, chat_id, text, reply_markup=None):
        params = {"chat_id": chat_id, "text": text}
        if reply_markup:
            params["reply_markup"] = reply_markup
        return self.request("sendMessage", params)

    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            return self.request("sendSticker", params={"chat_id": chat_id}, files={"sticker": f})

    def download_file(self, file_id, dest_path):
        file_info = self.request("getFile", {"file_id": file_id})
        file_path = file_info["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        r = requests.get(url)
        with open(dest_path, "wb") as f:
            f.write(r.content)
        logger.info(f"📥 File downloaded: {dest_path}")
        return dest_path

    def set_webhook(self, url):
        return self.request("setWebhook", params={"url": url})

    # ➕ اینو اضافه کن: بررسی عضویت کاربر در کانال
    def is_user_in_channel(self, user_id, channel_username):
        try:
            res = self.request("getChatMember", {
                "chat_id": channel_username,
                "user_id": user_id
            })
            status = res["result"]["status"]
            return status in ["member", "administrator", "creator"]
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False
