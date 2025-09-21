import logging
from config import BOT_TOKEN
from utils.telegram_api import TelegramAPI
from handlers.messages import send_main_menu

logger = logging.getLogger(__name__)
api = TelegramAPI(BOT_TOKEN)


def handle_callback(callback_query):
    chat_id = callback_query["message"]["chat"]["id"]
    data = callback_query["data"]
    logger.info(f"📩 handle_callback {chat_id}: {data}")

    try:
        if data == "main_menu":
            send_main_menu(chat_id)

        elif data == "ai":
            api.send_message(chat_id, "🤖 بگو چی می‌خوای بدونی یا تولید کنم برات.")

        elif data == "sticker":
            api.send_message(chat_id, "🎭 عکس یا متن بده تا استیکر بسازم برات.")

        elif data == "help":
            api.send_message(
                chat_id,
                "ℹ️ راهنما:\n\n"
                "1️⃣ برای شروع /start رو بزن.\n"
                "2️⃣ باید عضو کانال @{CHANNEL_USERNAME} باشی.\n"
                "3️⃣ از منو می‌تونی استیکر بسازی یا از هوش مصنوعی استفاده کنی."
            )

        else:
            api.send_message(chat_id, "❌ دستور ناشناخته است.")
    except Exception as e:
        logger.error(f"❌ Error handling callback: {e}")
