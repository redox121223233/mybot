# utils/telegram_api.py
import requests
import json
import logging
import os

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str):
        if not token:
            raise ValueError("Token is required")
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_base = f"https://api.telegram.org/file/bot{token}"
        # try getMe to fetch username (optional, log on failure)
        try:
            info = self.request("getMe")
            self.username = info.get("result", {}).get("username", None)
            logger.info(f"Telegram bot username: {self.username}")
        except Exception as e:
            logger.error(f"getMe failed: {e}")
            self.username = None

    def request(self, method: str, params=None, files=None, timeout=15):
        url = f"{self.base_url}/{method}"
        try:
            # send params in body (application/x-www-form-urlencoded) or multipart when files present
            resp = requests.post(url, data=params, files=files, timeout=timeout)
            if resp.status_code != 200:
                raise Exception(f"❌ خطای HTTP {resp.status_code}: {resp.text}")
            return resp.json()
        except Exception as e:
            logger.error(f"❌ خطا در درخواست به تلگرام ({method}): {e}")
            raise

    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None, disable_web_page_preview=False):
        payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": disable_web_page_preview}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup is not None:
            # IMPORTANT: reply_markup must be a JSON-serialized string
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        resp = self.request("sendMessage", params=payload)
        logger.info(f"send_message: {resp}")
        return resp

    def send_sticker(self, chat_id, sticker_path):
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            resp = self.request("sendSticker", params={"chat_id": chat_id}, files=files)
            logger.info(f"send_sticker: {resp}")
            return resp

    def download_file(self, file_id, dest_path):
        resp = self.request("getFile", params={"file_id": file_id})
        file_path = resp["result"]["file_path"]
        file_url = f"{self.file_base}/{file_path}"

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        r = requests.get(file_url, stream=True, timeout=15)
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            logger.info(f"📥 File downloaded: {dest_path}")
        else:
            raise Exception(f"خطا در دانلود فایل: {r.text}")

    def set_webhook(self, url, certificate_path=None):
        files = None
        params = {"url": url}
        if certificate_path:
            files = {"certificate": open(certificate_path, "rb")}
        return self.request("setWebhook", params=params, files=files)

    # sticker set helpers
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
            resp = self.request("getStickerSet", params={"name": name})
            return resp.get("ok", False)
        except Exception:
            return False

    # getChatMember wrapper
    def get_chat_member(self, chat_id, user_id):
        return self.request("getChatMember", params={"chat_id": chat_id, "user_id": user_id})

    def is_user_in_channel(self, channel_username, user_id):
        try:
            if channel_username.startswith("@"):
                channel_username = channel_username[1:]
            chat_id = f"@{channel_username}"
            resp = self.get_chat_member(chat_id, user_id)
            status = resp["result"]["status"]
            return status in ["member", "creator", "administrator"]
        except Exception as e:
            logger.error(f"❌ خطا در بررسی عضویت: {e}")
            return False
