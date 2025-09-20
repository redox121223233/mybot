from config import BOT_TOKEN, DATA_DIR as BASE_DIR
from utils.telegram_api import TelegramAPI
from services.database_manager import DatabaseManager
from services.subscription_manager import SubscriptionManager
from services.menu_manager import MenuManager
from services.sticker_manager import StickerManager
from services.ai_manager import AIManager
import logging

logger = logging.getLogger(__name__)

try:
    # سرویس‌های اصلی
    api = TelegramAPI(BOT_TOKEN)
    db_manager = DatabaseManager(BASE_DIR)

    # ماژول‌ها
    subscription_manager = SubscriptionManager(db_manager, "subscriptions.json")
    menu_manager = MenuManager(api, BOT_TOKEN)
    sticker_manager = StickerManager(api, BASE_DIR)  # ✅ اصلاح شد
    ai_manager = AIManager(api)

    logger.info("Legacy services initialized successfully.")

except Exception as e:
    logger.error(f"❌ خطا در مقداردهی Legacy services: {e}")
    raise
