# /app/services/subscription_manager.py

import os
import json

class SubscriptionManager:
    def __init__(self, db_manager, filename: str = "subscriptions.json"):
        """
        مدیریت اشتراک‌ها
        :param db_manager: شی DatabaseManager
        :param filename: فایل ذخیره‌سازی اشتراک‌ها
        """
        self.db_manager = db_manager
        self.filename = filename
        self.subscriptions = self._load()

    def _load(self):
        """بارگذاری اشتراک‌ها از فایل"""
        data = self.db_manager.load(self.filename)
        return data if data else {}

    def _save(self):
        """ذخیره اشتراک‌ها در فایل"""
        self.db_manager.save(self.filename, self.subscriptions)

    def add_subscription(self, user_id: int, plan: str, expiry: str):
        """افزودن یا بروزرسانی اشتراک کاربر"""
        self.subscriptions[str(user_id)] = {"plan": plan, "expiry": expiry}
        self._save()

    def get_subscription(self, user_id: int):
        """دریافت وضعیت اشتراک کاربر"""
        return self.subscriptions.get(str(user_id))

    def has_active_subscription(self, user_id: int):
        """بررسی فعال بودن اشتراک"""
        sub = self.get_subscription(user_id)
        if not sub:
            return False
        # اینجا میشه تاریخ انقضا رو هم چک کرد (فعلا ساده نگه داشتیم)
        return True

    def remove_subscription(self, user_id: int):
        """حذف اشتراک کاربر"""
        if str(user_id) in self.subscriptions:
            del self.subscriptions[str(user_id)]
            self._save()
