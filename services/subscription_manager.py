# /app/services/subscription_manager.py

import os
import json

class SubscriptionManager:
    def __init__(self, filename: str, db_manager):
        """
        مدیریت اشتراک‌ها
        :param filename: نام فایل ذخیره‌سازی
        :param db_manager: شی DatabaseManager
        """
        self.filename = filename
        self.db_manager = db_manager
        self.subscriptions = self._load()

    def _load(self):
        data = self.db_manager.load(self.filename)
        return data if data else {}

    def _save(self):
        self.db_manager.save(self.filename, self.subscriptions)

    def add_subscription(self, user_id: int, plan: str, expiry: str):
        self.subscriptions[str(user_id)] = {"plan": plan, "expiry": expiry}
        self._save()

    def get_subscription(self, user_id: int):
        return self.subscriptions.get(str(user_id))

    def has_active_subscription(self, user_id: int):
        sub = self.get_subscription(user_id)
        if not sub:
            return False
        return True  # TODO: بررسی تاریخ انقضا

    def remove_subscription(self, user_id: int):
        if str(user_id) in self.subscriptions:
            del self.subscriptions[str(user_id)]
            self._save()
