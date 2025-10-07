import requests
from config import BOT_TOKEN

# ✅ آدرس Railway
BASE_URL = "https://mybot-production-61d8.up.railway.app"
WEBHOOK_URL = f"{BASE_URL}/{BOT_TOKEN}"

def set_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(url, json={"url": WEBHOOK_URL})
    print("Set webhook response:", response.json())

if __name__ == "__main__":
    set_webhook()
