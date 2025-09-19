from pathlib import Path
import json, threading
BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
USER_FILE = DATA_DIR / "user_data.json"
_lock = threading.Lock()

def _load(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except:
            return default
    return default

def _save(path, data):
    with _lock:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_user_if_missing(chat_id):
    users = _load(USER_FILE, {})
    uid = str(chat_id)
    if uid not in users:
        users[uid] = {"mode": None, "ai_mode": False, "created_packs": [], "last_reset": 0}
        _save(USER_FILE, users)

def set_user_mode(chat_id, mode):
    users = _load(USER_FILE, {})
    uid = str(chat_id)
    users.setdefault(uid, {})["mode"] = mode
    _save(USER_FILE, users)

def get_user_state(chat_id):
    return _load(USER_FILE, {}).get(str(chat_id), {})
