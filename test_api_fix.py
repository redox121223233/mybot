#!/usr/bin/env python3
"""
Test script to verify API endpoints are working correctly
"""

import requests
import json
import base64
import io
from PIL import Image

def test_api_endpoints():
    base_url = "https://mybot32.vercel.app"
    
    print("🧪 Testing API endpoints...")
    
    # Test 1: Create default sticker
    print("\n1. Testing /api/create-default-sticker")
    try:
        payload = {
            "user_id": 123456,
            "text": "تست استیکر",
            "color": "#FFFFFF",
            "background_color": "#FF0000"
        }
        
        response = requests.post(f"{base_url}/api/create-default-sticker", json=payload, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success: {result.get('message', 'No message')}")
            print(f"   📏 Sticker data length: {len(result.get('sticker', ''))}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 2: Create text sticker
    print("\n2. Testing /api/create-text-sticker")
    try:
        payload = {
            "user_id": 123456,
            "text": "استیکر متنی پیشرفته",
            "color": "#00FF00",
            "background_color": "transparent",
            "font_size": 60
        }
        
        response = requests.post(f"{base_url}/api/create-text-sticker", json=payload, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success: {result.get('message', 'No message')}")
            print(f"   📏 Sticker data length: {len(result.get('sticker', ''))}")
            
            # Test if we can decode the sticker
            sticker_data = result.get('sticker', '')
            if sticker_data.startswith('data:image/webp;base64,'):
                b64_data = sticker_data.split(',')[1]
                try:
                    image_bytes = base64.b64decode(b64_data)
                    img = Image.open(io.BytesIO(image_bytes))
                    print(f"   🖼️  Image decoded successfully: {img.size}, Mode: {img.mode}")
                except Exception as img_e:
                    print(f"   ❌ Image decode failed: {img_e}")
        else:
            print(f"   ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 3: Test existing add-sticker-to-pack
    print("\n3. Testing /api/add-sticker-to-pack")
    try:
        # Create a simple test sticker
        test_img = Image.new('RGBA', (512, 512), (255, 0, 0, 255))
        buffer = io.BytesIO()
        test_img.save(buffer, format='WEBP')
        sticker_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        payload = {
            "user_id": 123456,
            "pack_name": "test_pack",
            "sticker": f"data:image/webp;base64,{sticker_b64}",
            "type": "simple"
        }
        
        response = requests.post(f"{base_url}/api/add-sticker-to-pack", json=payload, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_api_endpoints()