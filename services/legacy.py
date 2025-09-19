
from config import BOT_TOKEN, DATA_DIR as BASE_DIR
from utils.telegram_api import TelegramAPI
from services.database_manager import DatabaseManager
from services.subscription_manager import SubscriptionManager
from services.menu_manager import MenuManager
from services.sticker_manager import StickerManager
from services.ai_manager import AIManager

api = TelegramAPI(BOT_TOKEN)
db_manager = DatabaseManager(BASE_DIR)
subscription_manager = SubscriptionManager(db_manager, "subscriptions.json")
menu_manager = MenuManager(api, BOT_TOKEN)
sticker_manager = StickerManager(api, db_manager, "BASE_DIR")
ai_manager = AIManager(api)
