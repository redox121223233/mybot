import os, requests

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

def _post(method, payload):
    url = f"{API}{method}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"_post error for {method}:", e)
        return None

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    if show_alert:
        payload["show_alert"] = True
    return _post("answerCallbackQuery", payload)

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return _post("sendMessage", payload)

def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return _post("editMessageText", payload)

def register_webhook(app_url=None, secret_token=None):
    if not app_url:
        app_url = os.environ.get("APP_URL")
    if not app_url:
        print("APP_URL not set; cannot register webhook.")
        return None
    token = BOT_TOKEN
    url = f"{API}setWebhook"
    data = {"url": f"{app_url}/{token}"}
    if secret_token:
        data["secret_token"] = secret_token
    try:
        r = requests.post(url, json=data, timeout=10)
        print("Webhook set:", r.text)
        return r.json()
    except Exception as e:
        print("register_webhook error:", e)
        return None
