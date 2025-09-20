import requests
import logging
import os

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_url = f"https://api.telegram.org/file/bot{token}"
        self.username = self.get_bot_username()

    def get_bot_username(self):
        url = f"{self.base_url}/getMe"
        resp = requests.get(url).json()
        if resp.get("ok"):
            return resp["result"]["username"]
        return "unknown_bot"

    def send_message(self, chat_id, text, reply_markup=None):
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        requests.post(url, json=payload)

    def download_file(self, file_id, dest_path):
        # گرفتن مسیر فایل
        file_path_resp = requests.get(f"{self.base_url}/getFile", params={"file_id": file_id}).json()
        if not file_path_resp.get("ok"):
            raise Exception(f"❌ خطا در دریافت مسیر فایل: {file_path_resp}")

        file_path = file_path_resp["result"]["file_path"]
        file_url = f"{self.file_url}/{file_path}"

        # دانلود فایل
        r = requests.get(file_url)
        if r.status_code != 200:
            raise Exception(f"خطا در دانلود فایل: {r.text}")

        with open(dest_path, "wb") as f:
            f.write(r.content)

        logger.info(f"📥 File downloaded: {dest_path}")
        return dest_path

    # بررسی وجود پک
    def sticker_set_exists(self, name):
        url = f"{self.base_url}/getStickerSet"
        resp = requests.get(url, params={"name": name}).json()
        return resp.get("ok", False)

    # ساخت پک جدید
    def create_new_sticker_set(self, user_id, name, title, png_path, emoji="😀"):
        url = f"{self.base_url}/createNewStickerSet"
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": user_id,
                "name": name,
                "title": title,
                "emojis": emoji
            }
            resp = requests.post(url, data=data, files=files).json()

        if not resp.get("ok"):
            logger.error(f"❌ خطا در ساخت پک: {resp}")
            return False
        return True

    # اضافه کردن استیکر
    def add_sticker_to_set(self, user_id, name, png_path, emoji="😀"):
        url = f"{self.base_url}/addStickerToSet"
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            data = {
                "user_id": user_id,
                "name": name,
                "emojis": emoji
            }
            resp = requests.post(url, data=data, files=files).json()

        if not resp.get("ok"):
            logger.error(f"❌ خطا در اضافه کردن استیکر: {resp}")
            return False
        return True
