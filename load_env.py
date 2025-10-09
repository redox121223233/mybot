import os
from dotenv import load_dotenv

def load_environment():
    """Load environment variables from .env file"""
    # Load .env file
    load_dotenv()
    
    # Check if BOT_TOKEN is set
    bot_token = os.getenv('BOT_TOKEN')
    if bot_token:
        print(f"BOT_TOKEN loaded: {bot_token[:10]}...")
    else:
        print("BOT_TOKEN not found in environment")
    
    # Check if WEBHOOK_URL is set
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        print(f"WEBHOOK_URL loaded: {webhook_url}")
    else:
        print("WEBHOOK_URL not found in environment")

if __name__ == "__main__":
    load_environment()