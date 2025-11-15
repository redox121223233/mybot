#!/usr/bin/env python3

"""
Webhook Setter Script - تنظیم مجدد webhook
"""

import requests
import json
import os

def set_webhook():
    """تنظیم webhook برای ربات"""
    
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables")
        return False
    
    # URL باید با URL واقعی Vercel شما جایگزین شود
    # لطفاً URL خود را اینجا وارد کنید
    webhook_url = "https://your-vercel-app.vercel.app/api/webhook"
    
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
    """دریافت اطلاعات webhook فعلی"""
    
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables")
        return False
    
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
    
    try:
        print("🔍 Getting current webhook info...")
        
        response = requests.get(api_url, timeout=30)
        result = response.json()
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        return result.get("ok", False)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False

def delete_webhook():
    """حذف webhook فعلی"""
    
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables")
        return False
    
    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        print("🗑️  Deleting current webhook...")
        
        response = requests.post(api_url, timeout=30)
        result = response.json()
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        return result.get("ok", False)
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Webhook Management Tool")
    print("=" * 50)
    
    while True:
        print("\n📋 Menu:")
        print("1. Get current webhook info")
        print("2. Delete current webhook")
        print("3. Set new webhook")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            print("\n1️⃣ Getting webhook info...")
            get_webhook_info()
        elif choice == "2":
            print("\n2️⃣ Deleting webhook...")
            delete_webhook()
        elif choice == "3":
            print("\n3️⃣ Setting webhook...")
            set_webhook()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")