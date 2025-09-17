#!/usr/bin/env python3
# bot_clean.py - Refactored Telegram sticker bot (clean structure, unified sticker flow)
# NOTE: This is a refactor/skeleton of your original bot with main flows implemented.
# Make sure environment variables BOT_TOKEN, WEBHOOK_SECRET, APP_URL are set before running.
import os
import time
import json
import logging
from flask import Flask, request, jsonify
import requests

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot_clean")

# --- Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret").strip()
APP_URL = os.environ.get("APP_URL", "").strip().rstrip("/")
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# Simple in-memory DB (persisted to disk)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "user_data_clean.json")
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    except Exception as e:
        logger.error("Failed loading user data: %s", e)
        user_data = {}
else:
    user_data = {}

def save_user_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Failed to save user data: %s", e)

# --- HTTP helpers for Telegram API ---
def send_request(method, payload):
    url = API + method
    try:
        resp = requests.post(url, json=payload, timeout=10)
        logger.info("Telegram %s -> %s (status=%s)", method, payload.get("chat_id"), resp.status_code)
        try:
            return resp.json()
        except Exception:
            return {"ok": False, "status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        logger.error("Error calling Telegram API %s: %s", method, e)
        return {"ok": False, "error": str(e)}

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return send_request("sendMessage", payload)

def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return send_request("editMessageText", payload)

def answer_callback_query(callback_query_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text:
        payload["text"] = text
    return send_request("answerCallbackQuery", payload)

# --- Utilities ---
def get_lang(chat_id):
    return user_data.get(str(chat_id), {}).get("lang", "fa")

def ensure_user(chat_id):
    key = str(chat_id)
    if key not in user_data:
        user_data[key] = {
            "mode": None,       # e.g. "free", "ai", "advanced"
            "step": None,       # e.g. "pack_name", "text", "waiting_file"
            "pack_name": None,
            "background": None,
            "created_packs": [],
            "last_reset": time.time(),
        }
        save_user_data()
    return user_data[key]

# Placeholder for channel membership check (customize for your use-case)
def check_channel_membership(chat_id):
    # If you want to enforce channel membership, implement here.
    return True

# --- Sticker flow orchestrator ---
def start_sticker_flow(chat_id, mode="free"):
    """
    Initialize sticker creation flow for a user.
    mode: "free", "ai", "advanced", "template", etc.
    """
    u = ensure_user(chat_id)
    u["mode"] = mode
    u["step"] = "pack_name" if not u.get("pack_name") else "text"
    save_user_data()
    
    # Build an inline keyboard tailored to sticker flows
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔄 ساخت استیکر جدید", "callback_data": "new_sticker"}],
            [{"text": "📷 تغییر بکگراند", "callback_data": "change_background"}],
            [{"text": "🔙 بازگشت", "callback_data": "back_to_main"}]
        ]
    }
    
    text = "🎭 استیکرساز آماده است!\n\n"
    if mode == "ai":
        text += "🤖 حالت هوشمند فعال است. برای فعال‌سازی هوش مصنوعی روی دکمه زیر کلیک کنید.\n\n"
        keyboard["inline_keyboard"].insert(0, [{"text": "🤖 فعال کردن هوش مصنوعی", "callback_data": "ai_activate"}])
    elif mode == "advanced":
        text += "🎨 طراحی پیشرفته فعال است — فونت، رنگ و افکت‌ها را انتخاب کنید.\n\n"
    elif mode == "template":
        text += "📚 قالب‌های آماده: یکی را انتخاب کنید یا قالب جدید بسازید.\n\n"
    else:
        text += "از دکمه‌ها برای شروع استفاده کنید یا متن مورد نظر را ارسال کنید.\n\n"
    
    return send_message(chat_id, text, reply_markup=keyboard)

# --- Handlers ---
def handle_callback_query(update):
    cq = update.get("callback_query") or {}
    callback_id = cq.get("id")
    data = cq.get("data", "")
    message = cq.get("message", {}) or {}
    chat = message.get("chat", {}) or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    from_user = cq.get("from", {})
    
    logger.info("Callback query received: %s from %s", data, from_user.get("id"))
    # Acknowledge the callback quickly
    answer_callback_query(callback_id, text="در حال پردازش...")
    
    # Basic routing for callbacks used in sticker flow
    if data == "new_sticker":
        # set step to text entry
        u = ensure_user(chat_id)
        u["step"] = "text"
        save_user_data()
        edit_message_text(chat_id, message_id, "✍️ لطفاً متن استیکر را ارسال کنید:", reply_markup=None)
        return "ok"
    elif data == "change_background":
        u = ensure_user(chat_id)
        u["step"] = "background"
        save_user_data()
        edit_message_text(chat_id, message_id, "📷 لطفاً عکس بکگراند را ارسال کنید:", reply_markup=None)
        return "ok"
    elif data == "ai_activate":
        u = ensure_user(chat_id)
        u["ai_mode"] = True
        save_user_data()
        edit_message_text(chat_id, message_id, "🤖 هوش مصنوعی فعال شد!\n\n🔄 اکنون متن را ارسال کنید یا استیکر بسازید.", reply_markup=None)
        return "ok"
    elif data == "back_to_main":
        edit_message_text(chat_id, message_id, "✅ بازگشت به منوی اصلی", reply_markup=None)
        show_main_menu(chat_id)
        return "ok"
    elif data.startswith("sub_"):
        # subscription handling stub
        plan = data.replace("sub_", "")
        send_message(chat_id, f"درخواست خرید پلن: {plan}\n(این بخش نیازمند پیاده‌سازی پرداخت است)")
        return "ok"
    
    # Unknown callback
    logger.warning("Unknown callback data: %s", data)
    return "ok"

def process_message(update):
    message = update.get("message") or {}
    chat = message.get("chat", {}) or {}
    chat_id = chat.get("id")
    if not chat_id:
        return "no chat id"
    
    ensure_user(chat_id)
    
    # If it's a callback-related answer (handled elsewhere), ignore here
    text = message.get("text")
    if text:
        logger.info("Message from %s: %s", chat_id, text)
        # Commands
        if text == "/start":
            # Optionally enforce channel membership
            if not check_channel_membership(chat_id):
                send_message(chat_id, "⚠️ لطفاً عضو کانال شوید تا از ربات استفاده کنید.")
                return "ok"
            show_main_menu(chat_id)
            return "ok"
        # Main menu quick buttons -> all route into sticker flow
        if text in ["🎭 استیکرساز", "🎁 تست رایگان", "🎨 طراحی پیشرفته", "📚 قالب‌های آماده"]:
            if text == "🎭 استیکرساز":
                return start_sticker_flow(chat_id, mode="free")
            if text == "🎁 تست رایگان":
                return start_sticker_flow(chat_id, mode="free")
            if text == "🎨 طراحی پیشرفته":
                return start_sticker_flow(chat_id, mode="advanced")
            if text == "📚 قالب‌های آماده":
                return start_sticker_flow(chat_id, mode="template")
        
        # If user is in sticker flow, route based on user state
        u = user_data.get(str(chat_id), {})
        step = u.get("step")
        if step == "pack_name":
            # set pack name and move to text
            u["pack_name"] = text.strip()
            u["step"] = "text"
            save_user_data()
            send_message(chat_id, f"✅ نام پک ثبت شد: <b>{u['pack_name']}</b>\n\n✍️ حالا متن استیکر را بفرستید.")
            return "ok"
        elif step == "text":
            # Here you would call your sticker generation logic. We'll simulate creation.
            sticker_text = text.strip()
            # simulate sticker creation...
            send_message(chat_id, f"🖼️ استیکر با متن «{sticker_text}» ساخته شد. (شبیه‌سازی)")
            # record usage
            u.setdefault("created_packs", []).append({"text": sticker_text, "time": time.time()})
            save_user_data()
            return "ok"
        elif step == "background":
            # message may contain photo. For simplicity we accept any message and treat as background set.
            u["background"] = "received"  # in real, save file_id
            u["step"] = "text"
            save_user_data()
            send_message(chat_id, "✅ بکگراند تنظیم شد. اکنون متن استیکر را ارسال کنید.")
            return "ok"
        
        # Fallback: show main menu if no special flow
        show_main_menu(chat_id)
        return "ok"
    
    # Handle photos / stickers if needed (not implemented here)
    return "ok"

# --- Menus ---
def show_main_menu(chat_id):
    keyboard = {
        "keyboard": [
            ["🎭 استیکرساز", "🎁 تست رایگان"],
            ["🎨 طراحی پیشرفته", "📚 قالب‌های آماده"],
            ["⚙️ تنظیمات", "📞 پشتیبانی"]
        ],
        "resize_keyboard": True
    }
    send_message(chat_id, "👋 خوش آمدید! یکی از گزینه‌ها را انتخاب کنید:", reply_markup=keyboard)

# --- Flask app & webhook ---
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": time.time()})

@app.route(f"/webhook/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    logger.info("Update received: %s", json.dumps(update)[:1000])
    # Prioritize callback_query
    if "callback_query" in update:
        try:
            handle_callback_query(update)
            return "ok"
        except Exception as e:
            logger.exception("Error handling callback_query: %s", e)
            return "error", 500
    elif "message" in update:
        try:
            process_message(update)
            return "ok"
        except Exception as e:
            logger.exception("Error handling message: %s", e)
            return "error", 500
    return "ok"

# Utility to set webhook (run once manually)
def register_webhook():
    if not APP_URL:
        logger.error("APP_URL is not set; cannot register webhook automatically")
        return
    url = f"{API}setWebhook"
    webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
    payload = {"url": webhook_url, "allowed_updates": ["message", "callback_query"]}
    resp = requests.post(url, json=payload, timeout=10)
    logger.info("setWebhook response: %s", resp.text)
    return resp.json()

if __name__ == "__main__":
    # If you want to register webhook automatically, uncomment below (requires APP_URL)
    # register_webhook()
    port = int(os.environ.get("PORT", 5000))
    logger.info("Starting bot_clean on port %s", port)
    app.run(host="0.0.0.0", port=port)
