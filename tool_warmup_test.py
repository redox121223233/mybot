#!/usr/bin/env python3
"""
Tool Warmup Test Script
Testing various tool capabilities to ensure everything is working
"""

import os
import sys
import json
import tempfile
import subprocess
import requests
from datetime import datetime

def test_file_operations():
    """Test file creation, reading, and writing"""
    print("🔧 Testing file operations...")
    
    # Create test file
    test_content = f"Tool warmup test at {datetime.now()}"
    with open("test_file.txt", "w") as f:
        f.write(test_content)
    
    # Read test file
    with open("test_file.txt", "r") as f:
        read_content = f.read()
    
    assert read_content == test_content, "File content mismatch"
    print("✅ File operations test passed")
    
    # Clean up
    os.remove("test_file.txt")

def test_command_execution():
    """Test command execution"""
    print("🔧 Testing command execution...")
    
    # Test simple command
    result = subprocess.run(["echo", "hello"], capture_output=True, text=True)
    assert result.returncode == 0, "Command failed"
    assert "hello" in result.stdout, "Command output incorrect"
    
    # Test Python command
    result = subprocess.run([sys.executable, "-c", "print('Python works')"], capture_output=True, text=True)
    assert result.returncode == 0, "Python command failed"
    assert "Python works" in result.stdout, "Python output incorrect"
    
    print("✅ Command execution test passed")

def test_network_connectivity():
    """Test network connectivity"""
    print("🔧 Testing network connectivity...")
    
    try:
        response = requests.get("https://httpbin.org/get", timeout=10)
        assert response.status_code == 200, "HTTP request failed"
        data = response.json()
        assert "url" in data, "Response data incomplete"
        print("✅ Network connectivity test passed")
    except Exception as e:
        print(f"❌ Network connectivity test failed: {e}")
        raise

def test_image_processing():
    """Test image processing capabilities"""
    print("🔧 Testing image processing...")
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Test", fill='white')
        
        # Test saving to different formats
        img.save("test.png")
        img.save("test.webp", format='WebP')
        
        # Verify files exist
        assert os.path.exists("test.png"), "PNG file not created"
        assert os.path.exists("test.webp"), "WebP file not created"
        
        print("✅ Image processing test passed")
        
        # Clean up
        os.remove("test.png")
        os.remove("test.webp")
        
    except ImportError:
        print("❌ PIL not available for image processing test")
    except Exception as e:
        print(f"❌ Image processing test failed: {e}")
        raise

def test_json_operations():
    """Test JSON operations"""
    print("🔧 Testing JSON operations...")
    
    test_data = {
        "test": True,
        "timestamp": datetime.now().isoformat(),
        "numbers": [1, 2, 3, 4, 5]
    }
    
    # Write JSON
    with open("test.json", "w") as f:
        json.dump(test_data, f)
    
    # Read JSON
    with open("test.json", "r") as f:
        loaded_data = json.load(f)
    
    assert loaded_data["test"] == True, "JSON data mismatch"
    assert len(loaded_data["numbers"]) == 5, "JSON array size incorrect"
    
    print("✅ JSON operations test passed")
    
    # Clean up
    os.remove("test.json")

def test_telegram_bot_imports():
    """Test Telegram bot related imports"""
    print("🔧 Testing Telegram bot imports...")
    
    try:
        import telegram
        from telegram import Update, Bot
        from telegram.ext import Application, CommandHandler
        
        print("✅ Telegram bot imports test passed")
        
    except ImportError as e:
        print(f"❌ Telegram imports failed: {e}")
        # Don't raise error here as this might be expected in some environments

def test_arabic_text_processing():
    """Test Arabic text processing capabilities"""
    print("🔧 Testing Arabic text processing...")
    
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        
        arabic_text = "مرحبا بالعالم"
        reshaped_text = arabic_reshaper.reshape(arabic_text)
        displayed_text = get_display(reshaped_text)
        
        assert len(displayed_text) > 0, "Arabic text processing failed"
        print("✅ Arabic text processing test passed")
        
    except ImportError:
        print("❌ Arabic processing libraries not available")
    except Exception as e:
        print(f"❌ Arabic text processing test failed: {e}")

def run_all_tests():
    """Run all test functions"""
    print("🚀 Starting tool warmup tests...")
    print("=" * 50)
    
    tests = [
        test_file_operations,
        test_command_execution,
        test_network_connectivity,
        test_image_processing,
        test_json_operations,
        test_telegram_bot_imports,
        test_arabic_text_processing,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Tool warmup successful.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)