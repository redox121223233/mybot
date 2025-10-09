import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.webhook import handler

# Mock request object
class MockRequest:
    def __init__(self, method='POST', body=None):
        self.method = method
        self.body = body or '{}'

def test_webhook():
    """Test the webhook handler with a sample update"""
    # Check if BOT_TOKEN is loaded
    bot_token = os.getenv('BOT_TOKEN')
    if bot_token:
        print(f"BOT_TOKEN loaded: {bot_token[:10]}...")
    else:
        print("❌ BOT_TOKEN not found in environment")
        return
    
    # Sample /start command update
    update_data = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
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
            "date": 1700000000,
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
    
    # Create mock request
    request = MockRequest('POST', json.dumps(update_data))
    
    # Test the handler
    print("Testing webhook handler...")
    result = handler(request)
    
    print(f"Response: {result}")
    print("Webhook test completed!")

if __name__ == "__main__":
    test_webhook()