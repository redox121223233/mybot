import os
import requests
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("webhook_test")

# Get bot token from environment or input
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    BOT_TOKEN = input("Please enter your Telegram bot token: ")

# Get APP_URL from environment or input
APP_URL = os.environ.get("APP_URL")
if not APP_URL:
    APP_URL = input("Please enter your app URL (e.g., https://your-app.com): ")
    APP_URL = APP_URL.strip().rstrip('/')

# Get webhook secret
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "secret").strip()

# Telegram API URL
API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

def check_webhook_info():
    """Check current webhook information"""
    try:
        response = requests.get(f"{API}getWebhookInfo")
        result = response.json()
        logger.info(f"Current webhook info: {json.dumps(result, indent=2)}")
        return result
    except Exception as e:
        logger.error(f"Error checking webhook info: {e}")
        return None

def delete_webhook():
    """Delete current webhook"""
    try:
        response = requests.post(f"{API}deleteWebhook")
        result = response.json()
        logger.info(f"Delete webhook result: {result}")
        return result.get("ok", False)
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        return False

def set_webhook():
    """Set webhook with proper configuration"""
    try:
        webhook_url = f"{APP_URL}/webhook/{WEBHOOK_SECRET}"
        logger.info(f"Setting webhook to: {webhook_url}")
        
        data = {
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        }
        
        response = requests.post(f"{API}setWebhook", json=data)
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"✅ Webhook registered successfully: {result}")
            return True
        else:
            logger.error(f"❌ Failed to register webhook: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Error registering webhook: {e}")
        return False

def send_test_message():
    """Send a test message to the bot to check if it's working"""
    try:
        chat_id = input("Enter your Telegram chat ID to receive a test message: ")
        if not chat_id:
            logger.warning("No chat ID provided, skipping test message")
            return False
            
        data = {
            "chat_id": chat_id,
            "text": "🔄 Test message from webhook setup script"
        }
        
        response = requests.post(f"{API}sendMessage", json=data)
        result = response.json()
        
        if result.get("ok"):
            logger.info(f"✅ Test message sent successfully")
            return True
        else:
            logger.error(f"❌ Failed to send test message: {result}")
            return False
    except Exception as e:
        logger.error(f"❌ Error sending test message: {e}")
        return False

if __name__ == "__main__":
    print("🤖 Telegram Bot Webhook Test Script")
    print("==================================")
    
    # Check current webhook
    print("\n1. Checking current webhook configuration...")
    current_info = check_webhook_info()
    
    # Ask if user wants to reset webhook
    reset = input("\nDo you want to reset the webhook? (y/n): ").lower() == 'y'
    if reset:
        print("\n2. Deleting current webhook...")
        delete_webhook()
        
        print("\n3. Setting new webhook...")
        set_webhook()
        
        # Verify the new webhook
        print("\n4. Verifying new webhook configuration...")
        check_webhook_info()
    
    # Ask if user wants to send a test message
    test_msg = input("\nDo you want to send a test message? (y/n): ").lower() == 'y'
    if test_msg:
        print("\n5. Sending test message...")
        send_test_message()
    
    print("\n✅ Webhook test completed!")