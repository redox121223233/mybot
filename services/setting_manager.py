import os
import json
from config import DATA_DIR

# مسیر فایل تنظیمات کاربران
SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")

# تنظیمات پیش‌فرض برای هر کاربر
DEFAULT_SETTINGS = {
    "font": "default.ttf",
    "color": "black",
    "position": "center",
    "size": 24
}

# ---------- ابزار ذخیره‌سازی ----------
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- مدیریت تنظیمات ----------
def get_user_settings(user_id: int):
    data = load_settings()
    return data.get(str(user_id), DEFAULT_SETTINGS.copy())

def update_user_settings(user_id: int, key: str, value):
    data = load_settings()
    settings = data.get(str(user_id), DEFAULT_SETTINGS.copy())
    settings[key] = value
    data[str(user_id)] = settings
    save_settings(data)

def reset_user_settings(user_id: int):
    data = load_settings()
    data[str(user_id)] = DEFAULT_SETTINGS.copy()
    save_settings(data)
