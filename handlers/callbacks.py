import logging
from utils.telegram_api import TelegramAPI
from handlers.messages import send_main_menu

api = TelegramAPI()

def handle_callback(callback_query):
    data = callback_query["data"]
    chat_id = callback_query["message"]["chat"]["id"]

    logging.info(f"📩 handle_callback: {data}")

    if data == "restart_bot":
        send_main_menu(chat_id)
