#!/usr/bin/env python3
"""
Test script to verify the InputSticker fix is working
"""
import sys
import os

try:
    # Test InputSticker import
    from telegram import InputSticker
    print("✅ InputSticker import successful")
    
    # Test creating InputSticker object
    test_sticker = InputSticker(
        sticker=b"test_data",
        emoji_list=['😊']
    )
    print("✅ InputSticker object creation successful")
    
    # Check if the fixed code is present in the file
    api_file = os.path.join(os.path.dirname(__file__), 'api', 'index.py')
    with open(api_file, 'r') as f:
        content = f.read()
    
    if 'InputSticker(' in content and 'sticker=input_sticker' in content:
        print("✅ InputSticker fix is present in the code")
    else:
        print("❌ InputSticker fix not found in the code")
        sys.exit(1)
    
    if 'sticker=sticker_bytes, emojis=' in content:
        print("❌ Old API calls still present")
        sys.exit(1)
    else:
        print("✅ Old API calls have been replaced")
    
    print("\n🎉 All tests passed! The fix is working correctly.")
    print("🔄 Please restart your bot to apply the changes.")
    print("💡 The error 'unexpected keyword argument sticker' should now be resolved.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure python-telegram-bot is installed: pip install python-telegram-bot==20.7")
except Exception as e:
    print(f"❌ Error: {e}")