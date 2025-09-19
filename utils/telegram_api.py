import requests
from utils.logger import logger


class TelegramAPI:
    def __init__(self, token: str):
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, chat_id: int, text: str, reply_markup=None):
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup

        response = requests.post(url, json=payload)
        logger.info(f"send_message response: {response.text}")
        return response.json()

    def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup=None):
        url = f"{self.base_url}/editMessageText"
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup

        response = requests.post(url, json=payload)
        logger.info(f"edit_message_text response: {response.text}")
        return response.json()

    def answer_callback_query(self, callback_query_id: str, text: str = None, show_alert: bool = False):
        url = f"{self.base_url}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
        if text:
            payload["text"] = text

        response = requests.post(url, json=payload)
        logger.info(f"answer_callback_query response: {response.text}")
        return response.json()
