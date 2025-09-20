import os
import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}/"

        # گرفتن یوزرنیم ربات (برای ساخت پک استیکر)
        self.username = self.get_bot_username()

    # گرفتن یوزرنیم ربات
    def get_bot_username(self):
        url = f"{self.base_url}getMe"
        r = requests.get(url)
        if r.ok:
            return r.json()["result"]["username"]
        return "MyBot"

    # ارسال پیام متنی
    def send_message(self, chat_id, text, reply_markup=None):
        url = f"{self.base_url}sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        r = requests.post(url, json=payload)
        logger.info(f"send_message: {r.text}")
        return r.json()

    # ارسال عکس
    def send_photo(self, chat_id, photo_path, caption=None, reply_markup=None):
        url = f"{self.base_url}sendPhoto"
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
            if reply_markup:
                data["reply_markup"] = reply_markup
            r = requests.post(url, data=data, files=files)
        logger.info(f"send_photo: {r.text}")
        return r.json()

    # دانلود فایل (برای استیکر ساز)
    def download_file(self, file_id, dest_path):
        file_info = requests.get(f"{self.base_url}getFile?file_id={file_id}")
        if not file_info.ok:
            raise Exception(f"خطا در گرفتن فایل: {file_info.text}")

        file_path = file_info.json()["result"]["file_path"]
        file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"

        r = requests.get(file_url)
        if not r.ok:
            raise Exception(f"خطا در دانلود فایل: {r.text}")

        with open(dest_path, "wb") as f:
            f.write(r.content)

        logger.info(f"📥 File downloaded: {dest_path}")
        return dest_path

    # دکمه بازگشت
    def get_back_button(self):
        return {"keyboard": [["⬅️ بازگشت"]], "resize_keyboard": True}

    # منوی اصلی
    def main_menu(self):
        return {
            "keyboard": [
                ["🎭 استیکرساز", "🤖 هوش مصنوعی"],
                ["⭐ اشتراک", "🎁 تست رایگان"]
            ],
            "resize_keyboard": True
        }
