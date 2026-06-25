import json
import os
import base64
from typing import Dict, Any, List, Optional
from ..utils.helpers import _today_start_ts

STORAGE_FILE = "/tmp/bot_storage.json" if os.environ.get("VERCEL") else "bot_storage.json"

def _json_encode_helper(obj):
    if isinstance(obj, bytes):
        return {"__bytes__": base64.b64encode(obj).decode("utf-8")}
    return obj

def _json_decode_helper(obj):
    if isinstance(obj, dict) and "__bytes__" in obj:
        return base64.b64decode(obj["__bytes__"])
    return obj

class Storage:
    def __init__(self):
        self.USERS: Dict[str, Dict[str, Any]] = {}
        self.SESSIONS: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r") as f:
                    data = json.load(f, object_hook=_json_decode_helper)
                    self.USERS = data.get("users", {})
                    self.SESSIONS = data.get("sessions", {})
            except Exception as e:
                print(f"Error loading storage: {e}")

    def save(self):
        try:
            with open(STORAGE_FILE, "w") as f:
                json.dump({
                    "users": self.USERS,
                    "sessions": self.SESSIONS
                }, f, default=_json_encode_helper)
        except Exception as e:
            print(f"Error saving storage: {e}")

    def get_user(self, uid: int) -> Dict[str, Any]:
        uid_str = str(uid)
        if uid_str not in self.USERS:
            self.USERS[uid_str] = {
                "ai_used": 0,
                "vote": None,
                "day_start": _today_start_ts(),
                "packs": [],
                "current_pack": None,
                "daily_limit": None
            }
            self.save()
        return self.USERS[uid_str]

    def get_session(self, uid: int) -> Dict[str, Any]:
        uid_str = str(uid)
        if uid_str not in self.SESSIONS:
            self.reset_session(uid)
        return self.SESSIONS[uid_str]

    def reset_session(self, uid: int):
        uid_str = str(uid)
        self.SESSIONS[uid_str] = {
            "mode": "menu",
            "ai": {},
            "simple": {},
            "pack_wizard": {},
            "await_feedback": False,
            "last_sticker_format": "static",
            "current_pack_short_name": None,
            "current_pack_title": None,
            "admin": {}
        }
        self.save()

    def update_session(self, uid: int, data: Dict[str, Any]):
        uid_str = str(uid)
        if uid_str not in self.SESSIONS:
            self.reset_session(uid)
        self.SESSIONS[uid_str].update(data)
        self.save()

    def get_user_packs(self, uid: int) -> List[Dict[str, str]]:
        return self.get_user(uid).get("packs", [])

    def add_user_pack(self, uid: int, pack_name: str, pack_short_name: str):
        u = self.get_user(uid)
        packs = u.get("packs", [])
        if not any(p["short_name"] == pack_short_name for p in packs):
            packs.append({"name": pack_name, "short_name": pack_short_name})
        u["current_pack"] = pack_short_name
        self.save()

    def set_current_pack(self, uid: int, pack_short_name: str):
        self.get_user(uid)["current_pack"] = pack_short_name
        self.save()

    def get_current_pack(self, uid: int) -> Optional[Dict[str, str]]:
        u = self.get_user(uid)
        short_name = u.get("current_pack")
        return next((p for p in u.get("packs", []) if p["short_name"] == short_name), None)

# Global storage instance
storage = Storage()
