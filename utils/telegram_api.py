import requests
import logging

class TelegramAPI:
    def __init__(self, bot_token: str):
        self.base_url = f"https://api.telegram.org/bot{bot_token}/"

    def send_message(self, chat_id: int, text: str, reply_markup=None):
        url = self.base_url + "sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(url, json=payload)
        logging.info(f"send_message response: {response.text}")
        return response.json()

    def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup=None):
        url = self.base_url + "editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(url, json=payload)
        logging.info(f"edit_message_text response: {response.text}")
        return response.json()

def register_webhook(bot_token: str, url: str):
    base_url = f"https://api.telegram.org/bot{bot_token}/"
    set_webhook_url = base_url + "setWebhook"
    response = requests.post(set_webhook_url, json={"url": url})
    logging.info(f"register_webhook response: {response.text}")
    return response.json()
