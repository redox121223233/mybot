import logging
from config import BOT_TOKEN, DATA_DIR as BASE_DIR
from utils.telegram_api import TelegramAPI
from services.database_manager import DatabaseManager
from services.subscription_manager import SubscriptionManager
from services.menu_manager import MenuManager
from services.sticker_manager import StickerManager
from services.ai_manager import AIManager

# لاگر برای خطاها و لاگ‌ها
logger = logging.getLogger(__name__)

try:
    # اتصال به API تلگرام
    api = TelegramAPI(BOT_TOKEN)

    # مدیریت دیتابیس (فایل‌های JSON داخل BASE_DIR)
    db_manager = DatabaseManager(BASE_DIR)

    # مدیریت اشتراک‌ها
    subscription_manager = SubscriptionManager(db_manager, "subscriptions.json")

    # مدیریت منو و دکمه‌ها
    menu_manager = MenuManager(api, BOT_TOKEN)

    # مدیریت استیکرها
    # ⚠️ اینجا BASE_DIR باید بدون کوتیشن باشه، چون مسیر هست نه رشته
    sticker_manager = StickerManager(api, db_manager, BASE_DIR)

    # مدیریت هوش مصنوعی (برای استیکرهای هوشمند)
    ai_manager = AIManager(api)

    logger.info("✅ Legacy services initialized successfully.")

except Exception as e:
    logger.error(f"❌ خطا در مقداردهی Legacy services: {e}")
    raise
