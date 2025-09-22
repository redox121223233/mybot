import os
import json
from config import DATA_DIR, DEFAULT_SETTINGS

SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_settings(user_id):
    data = load_settings()
    return data.get(str(user_id), DEFAULT_SETTINGS.copy())

def update_user_settings(user_id, key, value):
    data = load_settings()
    settings = data.get(str(user_id), DEFAULT_SETTINGS.copy())
    settings[key] = value
    data[str(user_id)] = settings
    save_settings(data)

def reset_user_settings(user_id):
    data = load_settings()
    data[str(user_id)] = DEFAULT_SETTINGS.copy()
    save_settings(data)
