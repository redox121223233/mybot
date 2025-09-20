# utils/telegram_api.py
import os
import json
import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_url = f"https://api.telegram.org/file/bot{token}"

    def _post(self, method, data=None, files=None):
        url = f"{self.base_url}/{method}"
        try:
            if files:
                r = requests.post(url, data=data, files=files, timeout=30)
            else:
                r = requests.post(url, json=data, timeout=30)
            return r.json()
        except Exception as e:
            logger.exception("HTTP request failed")
            raise

    def send_message(self, chat_id, text, reply_markup=None):
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            # reply_markup must be JSON string in Telegram API
            if not isinstance(reply_markup, str):
                data["reply_markup"] = json.dumps(reply_markup)
            else:
                data["reply_markup"] = reply_markup
        return self._post("sendMessage", data)

    def send_photo(self, chat_id, photo_path, caption=None):
        url = f"{self.base_url}/sendPhoto"
        with open(photo_path, "rb") as photo:
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
            r = requests.post(url, data=data, files={"photo": photo}, timeout=60)
            try:
                return r.json()
            except:
                return {"ok": False, "error": "invalid response from telegram"}

    def send_sticker(self, chat_id, sticker_path):
        url = f"{self.base_url}/sendSticker"
        with open(sticker_path, "rb") as f:
            data = {"chat_id": chat_id}
            r = requests.post(url, data=data, files={"sticker": f}, timeout=60)
            try:
                return r.json()
            except:
                return {"ok": False, "error": "invalid response from telegram"}

    def get_file_path(self, file_id):
        """call getFile and return file_path (string)"""
        resp = requests.get(f"{self.base_url}/getFile", params={"file_id": file_id}, timeout=15)
        data = resp.json()
        if not data.get("ok"):
            raise Exception(f"getFile failed: {data}")
        return data["result"]["file_path"]

    def download_file(self, file_id_or_path, dest_path=None):
        """
        Accept either a Telegram file_id (e.g. 'AgACAg...') or a file_path returned by getFile.
        Returns local path where file was saved.
        """
        # determine file_path on server
        try:
            if isinstance(file_id_or_path, str) and "/" in file_id_or_path:
                file_path = file_id_or_path  # already a file_path
            else:
                file_path = self.get_file_path(file_id_or_path)
        except Exception as e:
            raise Exception(f"خطا در گرفتن فایل از تلگرام: {e}")

        url = f"{self.file_url}/{file_path}"
        r = requests.get(url, stream=True, timeout=30)
        if r.status_code != 200:
            raise Exception(f"خطا در دانلود فایل: {r.status_code} - {r.text}")

        if dest_path is None:
            dest_path = os.path.join("/tmp", os.path.basename(file_path))
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(4096):
                if chunk:
                    f.write(chunk)
                        def get_back_button(self):
        return {"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}

    def main_menu(self):
        return {
            "keyboard": [
                ["🎭 استیکرساز", "🤖 هوش مصنوعی"],
                ["⭐ اشتراک", "🎁 تست رایگان"]
            ],
            "resize_keyboard": True
        }


        logger.info(f"File downloaded: {dest_path}")
        return dest_path
