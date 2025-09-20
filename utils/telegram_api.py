import os
import requests
import logging


class TelegramAPI:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.file_url = f"https://api.telegram.org/file/bot{token}"

    def get_file(self, file_id):
        """📂 گرفتن مسیر فایل از تلگرام"""
        url = f"{self.base_url}/getFile"
        response = requests.post(url, data={"file_id": file_id}).json()
        if response.get("ok"):
            return response["result"]["file_path"]
        raise Exception(f"خطا در گرفتن فایل: {response}")

    def download_file(self, file_path, save_dir="/tmp"):
        """⬇️ دانلود فایل از تلگرام"""
        url = f"{self.file_url}/{file_path}"
        local_path = os.path.join(save_dir, os.path.basename(file_path))
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            logging.info(f"File downloaded: {local_path}")
            return local_path
        else:
            raise Exception(f"خطا در دانلود فایل: {response.text}")

    def send_message(self, chat_id, text, reply_markup=None):
        """✉️ ارسال پیام"""
        url = f"{self.base_url}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
        if reply_markup:
            data["reply_markup"] = reply_markup
        requests.post(url, json=data)

    def send_photo(self, chat_id, photo_path, caption=None):
        """📷 ارسال عکس"""
        url = f"{self.base_url}/sendPhoto"
        with open(photo_path, "rb") as photo:
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
            response = requests.post(url, data=data, files={"photo": photo})
        return response.json()
