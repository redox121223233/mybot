import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_test_message():
    """Send a test message to the bot"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment")
        return False
    
    # Replace with your Telegram user ID or a test chat ID
    chat_id = "6053579919"  # This should be your Telegram user ID
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": "This is a test message from the bot management system"
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("✅ Test message sent successfully!")
            return True
        else:
            print(f"❌ Failed to send test message: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False

if __name__ == "__main__":
    print("Sending test message to bot...")
    success = send_test_message()
    
    if success:
        print("\n✅ Test message sent!")
    else:
        print("\n❌ Failed to send test message.")