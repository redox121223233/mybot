
from utils.logger import logger
from services.database_manager import DatabaseManager

class SubscriptionManager:
    def __init__(self, db_manager: DatabaseManager, filename: str = "subscriptions.json"):
        if not hasattr(db_manager, "load") or not hasattr(db_manager, "save"):
            raise ValueError("db_manager باید یک شی از DatabaseManager باشد.")
        self.db = db_manager
        self.filename = filename
        self.subscriptions = self.db.load(self.filename) or {}

    def save(self):
        self.db.save(self.filename, self.subscriptions)

    def add_subscription(self, user_id: int, plan: str, expires_at: int):
        self.subscriptions[str(user_id)] = {"plan": plan, "expires_at": expires_at}
        self.save()

    def get_subscription(self, user_id: int):
        return self.subscriptions.get(str(user_id))

    def has_active(self, user_id: int):
        sub = self.get_subscription(user_id)
        if not sub: return False
        return sub.get("expires_at", 0) > __import__("time").time()
