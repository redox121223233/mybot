import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_inline_button():
    """Send a message with inline keyboard button to the bot"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment")
        return False
    
    # Replace with your Telegram user ID or a test chat ID
    chat_id = "6053579919"  # This should be your Telegram user ID
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": "Test message with inline button",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "Test Button",
                        "callback_data": "test_button"
                    }
                ]
            ]
        }
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print("✅ Message with inline button sent successfully!")
            return True
        else:
            print(f"❌ Failed to send message with inline button: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending message with inline button: {e}")
        return False

if __name__ == "__main__":
    print("Sending message with inline button to bot...")
    success = send_inline_button()
    
    if success:
        print("\n✅ Message with inline button sent!")
        print("Check your Telegram to see if the button appears.")
    else:
        print("\n❌ Failed to send message with inline button.")