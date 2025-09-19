# mybot/utils/telegram_api.py
import os
import requests
from utils.logger import logger

class TelegramAPI:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.file_url = f"https://api.telegram.org/file/bot{bot_token}"

    # --- send basic message ---
    def send_message(self, chat_id, text, reply_markup=None):
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            r = requests.post(url, json=payload, timeout=15)
            logger.info("send_message: %s", r.text)
            return r.json()
        except Exception as e:
            logger.exception("send_message failed: %s", e)
            return None

    # --- send file (document) ---
    def send_document(self, chat_id, file_path, caption=None):
        url = f"{self.base_url}/sendDocument"
        files = {"document": open(file_path, "rb")}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        try:
            r = requests.post(url, data=data, files=files, timeout=30)
            logger.info("send_document: %s", r.text)
            return r.json()
        except Exception as e:
            logger.exception("send_document failed: %s", e)
            return None

    # --- send file (photo) ---
    def send_photo(self, chat_id, file_path, caption=None):
        url = f"{self.base_url}/sendPhoto"
        files = {"photo": open(file_path, "rb")}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        try:
            r = requests.post(url, data=data, files=files, timeout=30)
            logger.info("send_photo: %s", r.text)
            return r.json()
        except Exception as e:
            logger.exception("send_photo failed: %s", e)
            return None

    # --- getFile API ---
    def get_file(self, file_id, save_dir="/tmp"):
        """
        Download a Telegram file by file_id and save to save_dir.
        Returns local file path or None.
        """
        try:
            # step 1: call getFile
            url = f"{self.base_url}/getFile"
            r = requests.post(url, json={"file_id": file_id}, timeout=15)
            res = r.json()
            if not res.get("ok"):
                logger.error("get_file failed: %s", res)
                return None
            file_path = res["result"]["file_path"]

            # step 2: download actual file
            download_url = f"{self.file_url}/{file_path}"
            local_path = os.path.join(save_dir, os.path.basename(file_path))
            os.makedirs(save_dir, exist_ok=True)
            with requests.get(download_url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
            logger.info("File downloaded: %s", local_path)
            return local_path
        except Exception as e:
            logger.exception("get_file failed: %s", e)
            return None
