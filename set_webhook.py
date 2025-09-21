import requests
from config import BOT_TOKEN

# 🔹 اینجا دامنه خودت رو بذار
DOMAIN = "mybot-production-61d8.up.railway.app"   # ⚠️ تغییر بده به آدرس سرور خودت
WEBHOOK_URL = f"{DOMAIN}/{BOT_TOKEN}"


def set_webhook():
    """ست کردن وبهوک"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    print("✅ set_webhook:", response.json())


def remove_webhook():
    """حذف وبهوک فعلی"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    response = requests.post(url)
    print("🗑 remove_webhook:", response.json())


def get_webhook_info():
    """گرفتن اطلاعات وبهوک فعلی"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    response = requests.get(url)
    print("ℹ️ get_webhook_info:", response.json())


if __name__ == "__main__":
    print("👉 انتخاب کن:")
    print("1️⃣ ست کردن وبهوک")
    print("2️⃣ حذف وبهوک")
    print("3️⃣ گرفتن اطلاعات وبهوک")

    choice = input("شماره رو وارد کن: ")

    if choice == "1":
        set_webhook()
    elif choice == "2":
        remove_webhook()
    elif choice == "3":
        get_webhook_info()
    else:
        print("❌ گزینه نامعتبر")

