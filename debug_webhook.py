#!/usr/bin/env python3

"""
Debug Webhook Script - برای عیب‌یابی webhook
"""

import requests
import json
import os

def test_webhook_endpoint():
    """تست endpoint وبهوک"""
    
    # URL مورد نظر برای تست (باید با URL Vercel شما جایگزین شود)
    # لطفاً URL خود را اینجا وارد کنید
    webhook_url = "https://your-vercel-app.vercel.app/api/webhook"
    
    # ایجاد یک test payload
    test_payload = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Test",
                "username": "test_user",
                "type": "private"
            },
            "date": 1640995200,
            "text": "/start"
        }
    }
    
    try:
        print(f"🔍 Testing webhook endpoint: {webhook_url}")
        print("📤 Sending test payload...")
        
        response = requests.post(
            webhook_url,
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.text}")
        print(f"📄 Headers: {dict(response.headers)}")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def test_home_endpoint():
    """تست endpoint اصلی"""
    
    # URL مورد نظر برای تست
    home_url = "https://your-vercel-app.vercel.app/"
    
    try:
        print(f"🔍 Testing home endpoint: {home_url}")
        
        response = requests.get(home_url, timeout=30)
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response: {response.text}")
        
        return response.status_code == 200
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting webhook debug...")
    print("=" * 50)
    
    # ابتدا home endpoint را تست می‌کنیم
    print("1️⃣ Testing home endpoint:")
    home_ok = test_home_endpoint()
    
    print("\n" + "=" * 50)
    
    # سپس webhook endpoint را تست می‌کنیم
    print("2️⃣ Testing webhook endpoint:")
    webhook_ok = test_webhook_endpoint()
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    print(f"   Home Endpoint: {'✅ OK' if home_ok else '❌ FAILED'}")
    print(f"   Webhook Endpoint: {'✅ OK' if webhook_ok else '❌ FAILED'}")
    
    if not home_ok or not webhook_ok:
        print("\n🔧 Troubleshooting steps:")
        print("   1. Check if the app is deployed in Vercel")
        print("   2. Verify the correct URL")
        print("   3. Check Vercel Function Logs")
        print("   4. Verify BOT_TOKEN is set in environment variables")