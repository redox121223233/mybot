
import requests
from utils.logger import logger
from config import BOT_TOKEN

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

class TelegramAPI:
    def __init__(self, token=None):
        self.token = token or BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}/"

    def send_message(self, chat_id, text, reply_markup=None, parse_mode="HTML"):
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        try:
            r = requests.post(self.base_url + "sendMessage", json=payload, timeout=10)
            logger.info("send_message: %s", r.text)
            return r.json()
        except Exception as e:
            logger.exception("send_message error: %s", e)
            return None

    def edit_message_text(self, chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        try:
            r = requests.post(self.base_url + "editMessageText", json=payload, timeout=10)
            logger.info("edit_message_text: %s", r.text)
            return r.json()
        except Exception as e:
            logger.exception("edit_message_text error: %s", e)
            return None

    def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            payload["text"] = text
        try:
            r = requests.post(self.base_url + "answerCallbackQuery", json=payload, timeout=10)
            logger.info("answer_callback_query: %s", r.text)
            return r.json()
        except Exception as e:
            logger.exception("answer_callback_query error: %s", e)
            return None

def register_webhook(token, webhook_url):
    url = f"https://api.telegram.org/bot{token}/setWebhook"
    try:
        r = requests.post(url, json={"url": webhook_url}, timeout=10)
        logger.info("register_webhook: %s", r.text)
        return r.json()
    except Exception as e:
        logger.exception("register_webhook error: %s", e)
        return None
