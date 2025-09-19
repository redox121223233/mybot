# /app/services/subscription_manager.py

import os
import json

class SubscriptionManager:
    def __init__(self, db_manager, filename):
        if not hasattr(db_manager, "load") or not hasattr(db_manager, "save"):
            raise ValueError("db_manager باید یک شی از DatabaseManager باشد.")
        
        self.db_manager = db_manager   # ✅ درست شد
        self.filename = filename
        self.subscriptions = self._load()

    def _load(self):
        data = self.db_manager.load(self.filename)
        return data if data else {}

    def _save(self):
        self.db_manager.save(self.filename, self.subscriptions)

    def add_subscription(self, user_id, plan):
        self.subscriptions[user_id] = plan
        self._save()

    def get_subscription(self, user_id):
        return self.subscriptions.get(user_id)

    def remove_subscription(self, user_id):
        if user_id in self.subscriptions:
            del self.subscriptions[user_id]
            self._save()
