import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_telegram_webhook():
    """Test the Telegram webhook by sending a sample update"""
    # Get webhook URL
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("❌ WEBHOOK_URL not found in environment")
        return
    
    print(f"Testing webhook at: {webhook_url}")
    
    # Sample /start command update (similar to what Telegram sends)
    update_data = {
        "update_id": 987654321,
        "message": {
            "message_id": 2,
            "from": {
                "id": 6053579919,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser",
                "language_code": "en"
            },
            "chat": {
                "id": 6053579919,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1700000001,
            "text": "/start",
            "entities": [
                {
                    "offset": 0,
                    "length": 6,
                    "type": "bot_command"
                }
            ]
        }
    }
    
    # Send POST request to webhook
    try:
        response = requests.post(webhook_url, json=update_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook test successful!")
        else:
            print("❌ Webhook test failed!")
            
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")

if __name__ == "__main__":
    test_telegram_webhook()