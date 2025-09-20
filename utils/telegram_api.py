import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}/"
        self.username = None  # در صورت نیاز توکن بگیر
        self._get_me()

    def _get_me(self):
        try:
            response = requests.get(self.base_url + "getMe")
            if response.ok:
                data = response.json()
                self.username = data["result"]["username"]
        except Exception as e:
            logger.error(f"❌ خطا در getMe: {e}")

    def send_message(self, chat_id, text, reply_markup=None):
        url = self.base_url + "sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(url, json=payload)
        logger.info(f"send_message: {response.text}")
        return response.json()

    def download_file(self, file_id, dest_path):
        file_info = requests.get(self.base_url + f"getFile?file_id={file_id}").json()
        file_path = file_info["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        response = requests.get(file_url)
        with open(dest_path, "wb") as f:
            f.write(response.content)
        logger.info(f"📥 File downloaded: {dest_path}")

    def create_new_sticker_set(self, user_id, name, title, png_path, emoji="😀"):
        url = self.base_url + "createNewStickerSet"
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            data = {"user_id": user_id, "name": name, "title": title, "emojis": emoji}
            response = requests.post(url, data=data, files=files)
        if not response.ok:
            logger.error(f"❌ خطا در ساخت پک: {response.text}")
            return False
        return True

    def add_sticker_to_set(self, user_id, name, png_path, emoji="😀"):
        url = self.base_url + "addStickerToSet"
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            data = {"user_id": user_id, "name": name, "emojis": emoji}
            response = requests.post(url, data=data, files=files)
        if not response.ok:
            logger.error(f"❌ خطا در اضافه کردن استیکر: {response.text}")
            return False
        return True

    def sticker_set_exists(self, name):
        url = self.base_url + f"getStickerSet?name={name}"
        response = requests.get(url)
        return response.ok

    def send_sticker(self, chat_id, sticker_path):
        """ارسال استیکر به کاربر"""
        url = self.base_url + "sendSticker"
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            data = {"chat_id": chat_id}
            response = requests.post(url, data=data, files=files)
        if not response.ok:
            logger.error(f"❌ خطا در ارسال استیکر: {response.text}")
            return False
        return True
