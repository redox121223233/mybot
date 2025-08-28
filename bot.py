import os
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from waitress import serve

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is not set!")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret")
APP_URL = os.environ.get("APP_URL")
PAYMENT_URL = os.environ.get("PAYMENT_URL", "https://example.com/pay")  # لینک درگاه
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# دیتابیس ساده
user_data = {}

app = Flask(__name__)


@app.route("/")
def home():
    return "✅ Bot is running!"


@app.post(f"/webhook/{WEBHOOK_SECRET}")
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    msg = update.get("message")
    callback = update.get("callback_query")

    # دکمه‌ها
    if callback:
        chat_id = callback["message"]["chat"]["id"]
        data = callback["data"]

        if data == "free_test":
            user_data[chat_id] = {"mode": "free", "count": 0}
            send_message(chat_id, "🎁 تست رایگان فعال شد.\nلطفاً متن استیکر رو بفرست.")

        elif data == "premium":
            # ارسال لینک پرداخت به جای فعال کردن مستقیم
            send_message(chat_id, f"💳 برای خرید اشتراک روی لینک زیر بزن:\n{PAYMENT_URL}?chat_id={chat_id}")

        elif data == "support":
            support_id = os.environ.get("SUPPORT_ID", "@YourSupportID")
            send_message(chat_id, f"📞 برای پشتیبانی با {support_id} در تماس باش.")

        elif data == "about":
            send_message(chat_id, "ℹ️ این ربات برای ساخت استیکر متنی است.\n- رایگان: ۵ بار\n- اشتراکی: نامحدود")

        return "ok"

    # پیام کاربر
    if msg and "text" in msg:
        chat_id = msg["chat"]["id"]
        text = msg["text"]

        if chat_id not in user_data:
            show_menu(chat_id)
            return "ok"

        mode = user_data[chat_id]["mode"]
        count = user_data[chat_id]["count"]

        if mode == "free" and count >= 5:
            send_message(chat_id, "❌ سهمیه رایگان تمام شد. برای ادامه باید اشتراک بخری.")
            show_menu(chat_id)
            return "ok"

        # ساخت استیکر ساده PNG (مرحله بعدی استیکر واقعی اضافه می‌کنیم)
        sticker_path = "sticker.png"
        make_text_sticker(text, sticker_path)

        # ارسال فایل PNG
        with open(sticker_path, "rb") as f:
            requests.post(
                API + "sendDocument",
                data={"chat_id": chat_id},
                files={"document": f},
            )

        user_data[chat_id]["count"] += 1

    return "ok"


# کال‌بک موفق پرداخت
@app.route("/payment/success")
def payment_success():
    chat_id = request.args.get("chat_id")
    if chat_id:
        user_data[int(chat_id)] = {"mode": "premium", "count": 0}
        send_message(chat_id, "✅ پرداخت موفق! اشتراک نامحدودت فعال شد 🎉")
    return "پرداخت شما با موفقیت انجام شد."


# ساخت استیکر PNG (فعلا ساده)
def make_text_sticker(text, path):
    img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))  # شفاف
    draw = ImageDraw.Draw(img)

    font_path = os.environ.get("FONT_PATH", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    font = ImageFont.truetype(font_path, 70)

    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    draw.text(((512 - w) / 2, (512 - h) / 2), text, fill="black", font=font)

    img.save(path, "PNG")


# منو اصلی
def show_menu(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "🎁 تست رایگان", "callback_data": "free_test"}],
            [{"text": "⭐ بخش اشتراکی", "callback_data": "premium"}],
            [{"text": "📞 پشتیبانی", "callback_data": "support"}],
            [{"text": "ℹ️ درباره ربات", "callback_data": "about"}],
        ]
    }
    requests.post(API + "sendMessage", json={
        "chat_id": chat_id,
        "text": "👋 خوش اومدی! یکی از گزینه‌ها رو انتخاب کن:",
        "reply_markup": keyboard
    })


# ارسال پیام
def send_message(chat_id, text):
    requests.post(API + "sendMessage", json={"chat_id": chat_id, "text": text})


if __name__ == "__main__":
    if APP_URL:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        resp = requests.get(API + f"setWebhook?url={webhook_url}")
        print("DEBUG setWebhook:", resp.json())

    port = int(os.environ.get("PORT", 8000))
    serve(app, host="0.0.0.0", port=port)
