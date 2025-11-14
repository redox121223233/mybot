#!/usr/bin/env python3
"""
Webhook Setter for Telegram Bot
Set this URL in your browser with your bot token to configure webhook
"""

import requests
import sys

def set_webhook(bot_token, webhook_url):
    """Set webhook for Telegram bot"""
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    data = {
        "url": webhook_url,
        "drop_pending_updates": True,
        "allowed_updates": ["message", "callback_query"]
    }
    
    try:
        response = requests.post(api_url, json=data, timeout=30)
        result = response.json()
        
        if result.get("ok"):
            return {
                "success": True,
                "message": "✅ Webhook successfully set!",
                "webhook_url": webhook_url,
                "bot_info": result.get("result", {})
            }
        else:
            return {
                "success": False,
                "error": result.get("description", "Unknown error"),
                "error_code": result.get("error_code")
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_webhook_info(bot_token):
    """Get current webhook info"""
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        response = requests.get(api_url, timeout=30)
        result = response.json()
        
        if result.get("ok"):
            return result.get("result", {})
        else:
            return {"error": result.get("description", "Unknown error")}
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("🤖 Telegram Bot Webhook Setter")
    print("=" * 40)
    
    # Check if token is provided as argument
    if len(sys.argv) > 1:
        bot_token = sys.argv[1]
    else:
        # Get token from input
        bot_token = input("Enter your bot token: ").strip()
    
    if not bot_token:
        print("❌ Bot token is required!")
        sys.exit(1)
    
    # Get webhook URL
    webhook_url = input("Enter your webhook URL (e.g., https://your-app.vercel.app/api/webhook): ").strip()
    
    if not webhook_url:
        print("❌ Webhook URL is required!")
        sys.exit(1)
    
    print(f"\n🔧 Setting webhook for bot...")
    print(f"📡 Webhook URL: {webhook_url}")
    
    # Set webhook
    result = set_webhook(bot_token, webhook_url)
    
    if result["success"]:
        print(f"\n{result['message']}")
        print(f"✅ URL: {result['webhook_url']}")
        print(f"🤖 Bot: @{result['bot_info'].get('username', 'Unknown')}")
        print(f"📋 Custom Cert: {'Yes' if result['bot_info'].get('has_custom_certificate') else 'No'}")
        
        # Get webhook info
        print(f"\n📊 Getting webhook info...")
        webhook_info = get_webhook_info(bot_token)
        
        if "error" not in webhook_info:
            print(f"🌐 Current webhook: {webhook_info.get('url', 'Not set')}")
            print(f"📈 Pending updates: {webhook_info.get('pending_update_count', 0)}")
            print(f"⏰ Last error: {webhook_info.get('last_error_message', 'None')}")
        
        print(f"\n🎉 Your bot is now ready to receive messages!")
        
    else:
        print(f"\n❌ Error setting webhook: {result['error']}")
        if result.get("error_code"):
            print(f"🔢 Error code: {result['error_code']}")
        
        print(f"\n🔧 Troubleshooting:")
        print(f"1. Check if your bot token is correct")
        print(f"2. Verify the webhook URL is accessible")
        print(f"3. Make sure your bot app is deployed and running")
        print(f"4. Check if the URL responds with HTTP 200 to POST requests")