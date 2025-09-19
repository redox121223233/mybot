# /app/services/database_manager.py

import os
import json

class DatabaseManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)

    def _get_path(self, filename: str):
        """آدرس کامل فایل رو برمی‌گردونه"""
        return os.path.join(self.base_dir, filename)

    def load(self, filename: str):
        """بارگذاری دیتا از فایل JSON"""
        path = self._get_path(filename)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save(self, filename: str, data: dict):
        """ذخیره دیتا در فایل JSON"""
        path = self._get_path(filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
