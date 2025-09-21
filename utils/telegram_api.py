# utils/telegram_api.py
import requests
import logging
import os

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str):
        if not token:
            raise ValueError("token is required")
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.file_base = f"https://api.telegram.org/file/bot{self.token}"
        self.username = None
        self._init_me()

    def _init_me(self):
        try:
            r = self.request("getMe")
            self.username = r.get("result", {}).get("username")
            logger.info(f"Telegram bot username: {self.username}")
        except Exception as e:
            logger.warning(f"getMe failed: {e}")

    def request(self, method: str, params: dict = None, files: dict = None, timeout: int = 30):
        url = f"{self.base_url}/{method}"
        try:
            if files:
                # params -> form fields when uploading files
                resp = requests.post(url, data=params or {}, files=files, timeout=timeout)
            else:
                resp = requests.post(url, json=params or {}, timeout=timeout)

            if resp.status_code != 200:
                raise Exception(f"❌ خطای HTTP {resp.status_code}: {resp.text}")
            return resp.json()
        except Exception as e:
            logger.error(f"❌ خطا در درخواست به تلگرام ({method}): {e}")
            raise

    # sendMessage
    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return self.request("sendMessage", params=payload)

    # sendSticker (supports uploading a PNG sticker file)
    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            return self.request("sendSticker", params={"chat_id": chat_id}, files=files)

    # createNewStickerSet / addStickerToSet
    def create_new_sticker_set(self, user_id, name, title, png_path, emoji="😀"):
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            params = {"user_id": user_id, "name": name, "title": title, "emojis": emoji}
            return self.request("createNewStickerSet", params=params, files=files)

    def add_sticker_to_set(self, user_id, name, png_path, emoji="😀"):
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            params = {"user_id": user_id, "name": name, "emojis": emoji}
            return self.request("addStickerToSet", params=params, files=files)

    def sticker_set_exists(self, name):
        try:
            r = self.request("getStickerSet", params={"name": name})
            return r.get("ok", False)
        except Exception:
            return False

    # getFile + download
    def get_file_path(self, file_id):
        r = self.request("getFile", params={"file_id": file_id})
        return r["result"]["file_path"]

    def download_file(self, file_id, dest_path):
        file_path = self.get_file_path(file_id)
        url = f"{self.file_base}/{file_path}"
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            raise Exception(f"خطا در دانلود فایل: {r.status_code} {r.text}")
        with open(dest_path, "wb") as f:
            f.write(r.content)
        logger.info(f"📥 File downloaded: {dest_path}")
        return dest_path

    # webhook
    def set_webhook(self, url):
        return self.request("setWebhook", params={"url": url})

    # channel membership
    def is_user_in_channel(self, channel_username, user_id):
        try:
            if channel_username.startswith("@"):
                channel_username = channel_username[1:]
            resp = self.request("getChatMember", params={"chat_id": f"@{channel_username}", "user_id": user_id})
            status = resp["result"]["status"]
            return status in ("member", "creator", "administrator")
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False
