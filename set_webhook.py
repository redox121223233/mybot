#!/usr/bin/env python3

"""
Webhook Setter Script - Updated to prevent whitespace issues
"""

import requests
import json
import os

def set_webhook():
    """Set the webhook for the bot, ensuring URL is clean."""
    
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables")
        return False
    
    # Ensure the webhook URL from environment variable or hardcoded is stripped of whitespace
    webhook_url = os.environ.get("VERCEL_URL", "https://mybot32.vercel.app/api/webhook").strip()
    
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    data = {
        "url": webhook_url,
        "drop_pending_updates": True
    }
    
    try:
        print(f"🔗 Setting webhook to: {webhook_url}")
        print("📤 Sending request to Telegram API...")
        
        response = requests.post(api_url, json=data, timeout=30)
        result = response.json()
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        if result.get("ok"):
            print("✅ Webhook set successfully!")
            return True
        else:
            print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False

def get_webhook_info():
    """Get current webhook info."""
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not found")
        return False
    
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(api_url, timeout=30)
        result = response.json()
        print(f"📋 Info: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get("ok", False)
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False

def delete_webhook():
    """Delete the current webhook."""
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not found")
        return False
    
    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        response = requests.post(api_url, timeout=30)
        result = response.json()
        print(f"🗑️ Deletion status: {json.dumps(result, indent=2, ensure_ascii=False)}")
        return result.get("ok", False)
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Webhook Management Tool")
    print("=" * 50)
    
    # Automatically set webhook upon execution, more CI/CD friendly
    print("\n1️⃣ Attempting to delete existing webhook...")
    delete_webhook()

    print("\n2️⃣ Attempting to set new webhook...")
    set_webhook()

    print("\n3️⃣ Verifying current webhook info...")
    get_webhook_info()
