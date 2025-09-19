users = {}

def add_user(chat_id):
    if chat_id not in users:
        users[chat_id] = {"mode": None}

def set_mode(chat_id, mode):
    if chat_id in users:
        users[chat_id]["mode"] = mode
