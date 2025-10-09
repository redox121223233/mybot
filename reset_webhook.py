import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.bot_functions import set_webhook_url

async def reset_webhook():
    """Reset the webhook URL"""
    webhook_url = os.getenv('WEBHOOK_URL')
    if not webhook_url:
        print("WEBHOOK_URL not found in environment variables")
        return False
    
    print(f"Setting webhook to: {webhook_url}")
    success = await set_webhook_url(webhook_url)
    if success:
        print("✅ Webhook set successfully")
    else:
        print("❌ Failed to set webhook")
    
    return success

if __name__ == "__main__":
    asyncio.run(reset_webhook())