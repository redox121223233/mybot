#!/usr/bin/env python3
"""
Test script for the sticker bot to verify functionality
"""

import asyncio
import json
import sys
import os
from unittest.mock import Mock

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot import build_application, render_image, _prepare_text

async def test_bot_initialization():
    """Test if bot can be initialized."""
    print("🔍 Testing bot initialization...")
    try:
        token = os.environ.get('BOT_TOKEN')
        if not token:
            print("❌ BOT_TOKEN not found in environment variables")
            return False
            
        app = build_application()
        print("✅ Bot application built successfully")
        return True
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")
        return False

def test_render_image():
    """Test the image rendering functionality."""
    print("🎨 Testing image rendering...")
    try:
        test_text = "سلام دنیا"
        image_bytes = render_image(test_text, "center", "center", "#FFFFFF", "medium")
        
        if image_bytes and len(image_bytes) > 0:
            print(f"✅ Image rendered successfully ({len(image_bytes)} bytes)")
            return True
        else:
            print("❌ Image rendering failed - no data returned")
            return False
    except Exception as e:
        print(f"❌ Image rendering failed: {e}")
        return False

def test_text_preparation():
    """Test text preparation for Arabic/Persian."""
    print("📝 Testing text preparation...")
    try:
        test_text = "سلام دنیا"
        prepared = _prepare_text(test_text)
        print(f"✅ Text preparation successful: '{test_text}' -> '{prepared}'")
        return True
    except Exception as e:
        print(f"❌ Text preparation failed: {e}")
        return False

def test_api_handler():
    """Test the API handler structure."""
    print("🌐 Testing API handler...")
    try:
        from api.index import handler
        print("✅ API handler imported successfully")
        return True
    except Exception as e:
        print(f"❌ API handler import failed: {e}")
        return False

def test_font_availability():
    """Test if font files are available."""
    print("🔤 Testing font availability...")
    try:
        from bot import FONT_FILE
        if FONT_FILE and os.path.exists(FONT_FILE):
            print(f"✅ Font found at: {FONT_FILE}")
            return True
        else:
            print("❌ Font file not found")
            return False
    except Exception as e:
        print(f"❌ Font test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting Sticker Bot Tests\n")
    
    tests = [
        test_font_availability,
        test_text_preparation,
        test_render_image,
        test_api_handler,
    ]
    
    # Add async test
    print("=" * 50)
    bot_test = await test_bot_initialization()
    tests.append(lambda: bot_test)
    
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if asyncio.iscoroutinefunction(test):
            result = await test()
        else:
            result = test()
        
        if result:
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot should work correctly.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())