import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_full_webhook():
    """Test the webhook with a complete /start command update"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("❌ WEBHOOK_URL not found in environment")
        return False
    
    print(f"Testing webhook at: {webhook_url}")
    
    # Sample /start command update (similar to what Telegram sends)
    update_data = {
        "update_id": 987654322,
        "message": {
            "message_id": 3,
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
            "date": 1700000002,
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
    
    try:
        # Send POST request to webhook
        response = requests.post(webhook_url, json=update_data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Webhook test successful!")
            return True
        else:
            print("❌ Webhook test failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error testing webhook: {e}")
        return False

if __name__ == "__main__":
    print("Testing full webhook functionality...")
    success = test_full_webhook()
    
    if success:
        print("\n✅ Webhook is working correctly!")
    else:
        print("\n❌ Webhook is not working properly.")