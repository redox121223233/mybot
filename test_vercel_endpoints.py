#!/usr/bin/env python3
"""
تست endpointهای Vercel
"""

import requests

# تنظیمات
BASE_URL = "https://mybot-xyz.vercel.app"

def test_endpoints():
    """تست تمام endpointهای Vercel"""
    endpoints = [
        "/",
        "/health", 
        "/webhook",
        "/api/index",
        "/api/webhook"
    ]
    
    print("🧪 تست endpointهای Vercel...")
    
    for endpoint in endpoints:
        try:
            url = BASE_URL + endpoint
            print(f"🔗 تست: {url}")
            
            # تست GET
            response = requests.get(url, timeout=10)
            print(f"   GET Status: {response.status_code}")
            if response.status_code != 404:
                print(f"   GET Response: {response.text[:100]}")
            
            # تست POST برای webhook
            if endpoint in ["/webhook", "/api/webhook"]:
                post_response = requests.post(
                    url,
                    json={"update_id": 123, "message": {"text": "/start", "chat": {"id": 123}}},
                    timeout=10
                )
                print(f"   POST Status: {post_response.status_code}")
                if post_response.status_code != 404:
                    print(f"   POST Response: {post_response.text[:100]}")
            
            print()
            
        except Exception as e:
            print(f"❌ خطا در تست {endpoint}: {e}")
            print()

if __name__ == "__main__":
    test_endpoints()