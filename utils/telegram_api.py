import requests
import logging
import os

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_url = f"https://api.telegram.org/file/bot{token}"

    # ------------------ درخواست عمومی ------------------
    def request(self, method: str, params=None, files=None):
        url = f"{self.base_url}/{method}"
        try:
            response = requests.post(url, params=params, files=files)
            if response.status_code != 200:
                raise Exception(f"❌ خطای HTTP {response.status_code}: {response.text}")
            data = response.json()
            if not data.get("ok", False):
                raise Exception(f"❌ خطای تلگرام: {data}")
            return data
        except Exception as e:
            logger.error(f"❌ خطا در درخواست به تلگرام ({method}): {e}")
            raise

    # ------------------ ارسال پیام ------------------
    def send_message(self, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        resp = self.request("sendMessage", params=payload)
        logger.info(f"send_message: {resp}")
        return resp

    # ------------------ ارسال استیکر ------------------
    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            resp = self.request("sendSticker", params={"chat_id": chat_id}, files=files)
            logger.info(f"send_sticker: {resp}")
            return resp

    # ------------------ دریافت اطلاعات فایل ------------------
    def get_file(self, file_id):
        """
        گرفتن مسیر فایل از تلگرام برای دانلود
        """
        resp = self.request("getFile", params={"file_id": file_id})
        return resp["result"]

    # ------------------ دانلود فایل ------------------
    def download_file(self, file_id, dest_path):
        file_info = self.get_file(file_id)
        file_path = file_info["file_path"]
        file_url = f"{self.file_url}/{file_path}"

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        r = requests.get(file_url)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            logger.info(f"📥 فایل دانلود شد: {dest_path}")
            return dest_path
        else:
            raise Exception(f"خطا در دانلود فایل: {r.text}")

    # ------------------ وبهوک ------------------
    def set_webhook(self, url):
        resp = self.request("setWebhook", params={"url": url})
        return resp

    # ------------------ مدیریت استیکر پک ------------------
    def create_new_sticker_set(self, user_id, name, title, png_path, emoji="😀"):
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            return self.request("createNewStickerSet", params={
                "user_id": user_id,
                "name": name,
                "title": title,
                "emojis": emoji
            }, files=files)

    def add_sticker_to_set(self, user_id, name, png_path, emoji="😀"):
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            return self.request("addStickerToSet", params={
                "user_id": user_id,
                "name": name,
                "emojis": emoji
            }, files=files)

    def sticker_set_exists(self, name):
        try:
            resp = self.request("getStickerSet", params={"name": name})
            return resp.get("ok", False)
        except:
            return False

    # ------------------ بررسی عضویت در کانال ------------------
    def is_user_in_channel(self, channel_username, user_id):
        try:
            if channel_username.startswith("@"):
                chat_id = channel_username
            else:
                chat_id = f"@{channel_username}"

            logger.info(f"🔍 Checking membership: chat_id={chat_id}, user_id={user_id}")

            resp = self.request("getChatMember", params={
                "chat_id": chat_id,
                "user_id": user_id
            })

            status = resp["result"]["status"]
            return status in ["member", "creator", "administrator"]

        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False
