#!/usr/bin/env python3
"""تنظیم webhook برای ربات تلگرام"""
import requests
import sys

BOT_TOKEN = "8324626018:AAEiEd_zcpuw10s1nIWr5bryj1yyZDX0yl0"
WEBHOOK_URL = "https://mybot-zx31.vercel.app/webhook"

def setup_webhook():
    """تنظیم webhook"""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

    # حذف webhook قبلی
    print("🗑️ حذف webhook قبلی...")
    delete_response = requests.post(f"{api_url}/deleteWebhook", json={"drop_pending_updates": True})
    print(f"حذف: {delete_response.json()}")

    # تنظیم webhook جدید
    print(f"\n🔧 تنظیم webhook جدید: {WEBHOOK_URL}")
    set_response = requests.post(
        f"{api_url}/setWebhook",
        json={
            "url": WEBHOOK_URL,
            "drop_pending_updates": True,
            "allowed_updates": ["message", "callback_query"]
        }
    )
    result = set_response.json()
    print(f"نتیجه: {result}")

    # بررسی وضعیت webhook
    print("\n📊 بررسی وضعیت webhook...")
    info_response = requests.get(f"{api_url}/getWebhookInfo")
    info = info_response.json()

    if info.get("ok"):
        webhook_info = info["result"]
        print(f"\n✅ وضعیت webhook:")
        print(f"   URL: {webhook_info.get('url', 'تنظیم نشده')}")
        print(f"   Pending: {webhook_info.get('pending_update_count', 0)}")
        print(f"   Last Error: {webhook_info.get('last_error_message', 'ندارد')}")
        print(f"   Last Error Date: {webhook_info.get('last_error_date', 'ندارد')}")

        if webhook_info.get('url') == WEBHOOK_URL:
            print("\n✅ webhook با موفقیت تنظیم شد!")
            return True
        else:
            print("\n❌ webhook تنظیم نشد!")
            return False
    else:
        print(f"❌ خطا: {info}")
        return False

def test_webhook():
    """تست webhook با ارسال پیام"""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}"

    print("\n🧪 تست webhook...")
    print("لطفاً به ربات پیام /start بفرستید و نتیجه را چک کنید.")

if __name__ == "__main__":
    if setup_webhook():
        test_webhook()
    else:
        sys.exit(1)
