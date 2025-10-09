import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def send_start_command():
    """Send a /start command to the bot"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment")
        return False
    
    # Replace with your Telegram user ID or a test chat ID
    chat_id = "6053579919"  # This should be your Telegram user ID
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    data = {
        "chat_id": chat_id,
        "text": "/start"
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("✅ /start command sent successfully!")
            return True
        else:
            print(f"❌ Failed to send /start command: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending /start command: {e}")
        return False

if __name__ == "__main__":
    print("Sending /start command to bot...")
    success = send_start_command()
    
    if success:
        print("\n✅ /start command sent!")
        print("Check your Telegram to see if the bot responds.")
    else:
        print("\n❌ Failed to send /start command.")