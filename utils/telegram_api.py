# utils/telegram_api.py
import requests
import json
import logging
from config import BOT_TOKEN

logger = logging.getLogger(__name__)


class TelegramAPI:
    def __init__(self, token=BOT_TOKEN):
        self.base_url = f"https://api.telegram.org/bot{token}"

    def request(self, method, params=None, files=None):
        """📡 ارسال درخواست به API تلگرام"""
        url = f"{self.base_url}/{method}"
        response = requests.post(url, data=params, files=files)

        if not response.ok:
            logger.error(f"❌ خطا در درخواست به تلگرام ({method}): {response.text}")
            raise Exception(f"❌ خطای HTTP {response.status_code}: {response.text}")

        return response.json()

    def send_message(self, chat_id, text, reply_markup=None):
        """📩 ارسال پیام متنی به کاربر"""
        payload = {
            "chat_id": chat_id,
            "text": text
        }

        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)

        logger.info(f"send_message: {payload}")
        resp = self.request("sendMessage", params=payload)
        return resp

    def send_photo(self, chat_id, photo_path, caption=None):
        """🖼 ارسال عکس"""
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            payload = {"chat_id": chat_id}
            if caption:
                payload["caption"] = caption
            return self.request("sendPhoto", params=payload, files=files)

    def send_sticker(self, chat_id, sticker_path):
        """🎭 ارسال استیکر"""
        with open(sticker_path, "rb") as f:
            files = {"sticker": f}
            payload = {"chat_id": chat_id}
            return self.request("sendSticker", params=payload, files=files)

    def get_file(self, file_id):
        """📂 دریافت اطلاعات فایل"""
        return self.request("getFile", params={"file_id": file_id})

    def download_file(self, file_id, dest_path):
        """⬇️ دانلود فایل از تلگرام"""
        file_info = self.get_file(file_id)
        file_path = file_info["result"]["file_path"]

        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        r = requests.get(url, stream=True)

        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return dest_path
        else:
            raise Exception(f"❌ خطا در دانلود فایل: {r.text}")

    # ==================== 🎭 مدیریت استیکرها ====================

    def sticker_set_exists(self, name):
        """بررسی وجود پک استیکر"""
        try:
            resp = self.request("getStickerSet", params={"name": name})
            return resp.get("ok", False)
        except Exception:
            return False

    def create_new_sticker_set(self, user_id, name, title, png_path, emoji="😀"):
        """ساخت پک استیکر جدید"""
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            payload = {
                "user_id": user_id,
                "name": name,
                "title": title,
                "emojis": emoji
            }
            return self.request("createNewStickerSet", params=payload, files=files)

    def add_sticker_to_set(self, user_id, name, png_path, emoji="😀"):
        """اضافه کردن استیکر به پک موجود"""
        with open(png_path, "rb") as f:
            files = {"png_sticker": f}
            payload = {
                "user_id": user_id,
                "name": name,
                "emojis": emoji
            }
            return self.request("addStickerToSet", params=payload, files=files)
