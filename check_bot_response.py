import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_bot_response():
    """Check if the bot responds to messages"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment")
        return False
    
    # Get updates from the bot
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                updates = data.get('result', [])
                if updates:
                    print(f"✅ Found {len(updates)} updates")
                    # Show the latest update
                    latest_update = updates[-1]
                    print(f"Latest update: {latest_update}")
                    return True
                else:
                    print("⚠️  No updates found")
                    return False
            else:
                print(f"❌ API error: {data.get('description')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking bot response: {e}")
        return False

if __name__ == "__main__":
    print("Checking bot responses...")
    success = check_bot_response()
    
    if success:
        print("\n✅ Bot is receiving updates!")
    else:
        print("\n❌ Bot is not receiving updates.")