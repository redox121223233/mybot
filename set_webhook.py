import os
import httpx

BOT_TOKEN = os.environ.get("BOT_TOKEN")
# IMPORTANT: Make sure this URL is correct and the deployment is active.
WEBHOOK_URL = "https://mybot32.vercel.app/api/index"

def set_webhook():
    """
    Sets the webhook for the Telegram bot.
    """
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    params = {"url": WEBHOOK_URL}

    try:
        with httpx.Client() as client:
            response = client.post(api_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes
            result = response.json()
            if result.get("ok"):
                print(f"Webhook set successfully to {WEBHOOK_URL}")
                print(f"Response: {result.get('description')}")
            else:
                print("Failed to set webhook.")
                print(f"Error code: {result.get('error_code')}")
                print(f"Description: {result.get('description')}")

    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}.")
        print(str(e))
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    set_webhook()
