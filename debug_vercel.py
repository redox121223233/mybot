#!/usr/bin/env python3
"""
اسکریپت دیباگ Vercel deployment
"""

import requests
import json

WEBHOOK_URL = "https://mybot-zx31.vercel.app"

def debug_vercel():
    """دیباگ Vercel"""
    try:
        print("🔍 دیباگ Vercel deployment...")
        
        # تست health endpoint
        health_url = f"{WEBHOOK_URL}/health"
        print(f"Testing: {health_url}")
        
        try:
            response = requests.get(health_url, timeout=15)
            print(f"Status Code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code != 200:
                print(f"❌ Health check failed with status {response.status_code}")
                
                # تست root endpoint
                root_url = WEBHOOK_URL
                print(f"\nTesting root: {root_url}")
                root_response = requests.get(root_url, timeout=15)
                print(f"Root Status: {root_response.status_code}")
                print(f"Root Response: {root_response.text[:500]}")
            
        except requests.exceptions.Timeout:
            print("❌ Request timed out")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    except Exception as e:
        print(f"❌ خطا در دیباگ: {e}")

if __name__ == "__main__":
    debug_vercel()