import os
import json
from config import DATA_DIR

# 📌 مسیر فایل تنظیمات کاربران
SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")

# 📌 تنظیمات پیش‌فرض
DEFAULT_SETTINGS = {
    "font": "default.ttf",
    "color": "black",
    "position": "center",
    "size": 32
}

# ------------------ ابزارهای مدیریت فایل ------------------
def load_settings():
    """لود کردن تمام تنظیمات ذخیره‌شده از فایل JSON"""
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_settings(data):
    """ذخیره‌سازی تنظیمات به فایل JSON"""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ------------------ فانکشن‌های مدیریت یوزر ------------------
def get_user_settings(user_id):
    """گرفتن تنظیمات کاربر (اگه نباشه پیش‌فرض)"""
    data = load_settings()
    return data.get(str(user_id), DEFAULT_SETTINGS.copy())

def update_user_settings(user_id, key, value):
    """آپدیت یک تنظیم خاص برای کاربر"""
    data = load_settings()
    settings = data.get(str(user_id), DEFAULT_SETTINGS.copy())
    settings[key] = value
    data[str(user_id)] = settings
    save_settings(data)

def reset_user_settings(user_id):
    """ریست کردن تنظیمات کاربر به حالت پیش‌فرض"""
    data = load_settings()
    data[str(user_id)] = DEFAULT_SETTINGS.copy()
    save_settings(data)
