#!/usr/bin/env python3
"""
Debug script to identify the Python process exit issue
"""

import os
import sys
import asyncio
import traceback

def test_imports():
    """Test all critical imports"""
    print("🔧 Testing imports...")
    try:
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
        from PIL import Image, ImageDraw, ImageFont
        import arabic_reshaper
        from bidi.algorithm import get_display
        import json
        import logging
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_bot_initialization():
    """Test bot initialization"""
    print("\n🤖 Testing bot initialization...")
    try:
        # Set a test token
        os.environ['BOT_TOKEN'] = 'test_token_for_debugging'
        
        from api.index import init_bot, application
        
        # Initialize the bot
        init_bot()
        
        if application:
            print("✅ Application object created")
            
            # Test initialization
            print("Testing Application.initialize()...")
            asyncio.run(application.initialize())
            print("✅ Application initialized successfully")
            
            return True
        else:
            print("❌ Application object is None")
            return False
            
    except Exception as e:
        print(f"❌ Bot initialization error: {e}")
        traceback.print_exc()
        return False

def test_handler_function():
    """Test the handler function"""
    print("\n📡 Testing handler function...")
    try:
        from api.index import handler, application
        
        # Mock request
        class MockRequest:
            def __init__(self, data):
                self._data = data
            
            def json(self):
                return self._data
        
        # Test with empty request
        mock_req = MockRequest({})
        result = handler(mock_req)
        print(f"Empty request result: {result}")
        
        # Test with valid update
        valid_update = {
            'update_id': 1,
            'message': {
                'message_id': 1,
                'from': {
                    'id': 123,
                    'first_name': 'Test',
                    'is_bot': False,
                    'language_code': 'en'
                },
                'chat': {
                    'id': 123,
                    'type': 'private'
                },
                'date': 1234567890,
                'text': '/start'
            }
        }
        
        mock_req = MockRequest(valid_update)
        result = handler(mock_req)
        print(f"Valid update result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Handler error: {e}")
        traceback.print_exc()
        return False

def test_image_processing():
    """Test image processing capabilities"""
    print("\n🖼️ Testing image processing...")
    try:
        from PIL import Image, ImageDraw, ImageFont
        import tempfile
        import io
        
        # Create a test image
        img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((256, 256), "Test", fill="#FFFFFF")
        
        # Test WebP output
        output = io.BytesIO()
        img.save(output, format='WebP', quality=95)
        output.seek(0)
        
        print(f"✅ WebP image created successfully ({len(output.getvalue())} bytes)")
        return True
        
    except Exception as e:
        print(f"❌ Image processing error: {e}")
        traceback.print_exc()
        return False

def test_arabic_processing():
    """Test Arabic text processing"""
    print("\n🌐 Testing Arabic text processing...")
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        
        arabic_text = "مرحبا بالعالم"
        reshaped_text = arabic_reshaper.reshape(arabic_text)
        displayed_text = get_display(reshaped_text)
        
        print(f"✅ Arabic processing successful: {displayed_text}")
        return True
        
    except Exception as e:
        print(f"❌ Arabic processing error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all debug tests"""
    print("🚀 Starting Bot Debug Suite")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Bot Initialization", test_bot_initialization),
        ("Handler Function", test_handler_function),
        ("Image Processing", test_image_processing),
        ("Arabic Processing", test_arabic_processing),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! The bot should work correctly.")
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        print("\n💡 Possible solutions:")
        print("1. Ensure BOT_TOKEN is set in production environment")
        print("2. Check Python version compatibility")
        print("3. Verify all dependencies are installed")
        print("4. Review the specific error messages above")

if __name__ == "__main__":
    main()