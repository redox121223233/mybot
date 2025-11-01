#!/usr/bin/env python3
"""
Test script for Vercel deployment (updated for unified bot structure)
"""

import sys
import os
import json
import importlib.util

def test_imports():
    """Test if required modules can be imported and vercel.json is valid"""
    try:
        print("✅ Python version:", sys.version)
        
        # Test if vercel.json is valid JSON
        with open('vercel.json', 'r') as f:
            config = json.load(f)
            print("✅ vercel.json is valid JSON")
            
            # Check build source
            build_src = config.get('builds', [{}])[0].get('src')
            if build_src == 'api/bot.py':
                print(f"✅ vercel.json build source is correct: {build_src}")
            else:
                print(f"❌ vercel.json build source is incorrect: {build_src}")
                return False

        return True
    except Exception as e:
        print(f"❌ Import or JSON test failed: {e}")
        return False

def test_file_structure():
    """Test if the required file exists"""
    required_files = [
        'api/bot.py',
        'vercel.json', 
        'requirements.txt',
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} is missing")
            all_exist = False
            
    return all_exist

def test_handler_structure():
    """Test if the handler in api/bot.py is a class inheriting from BaseHTTPRequestHandler"""
    try:
        # Check for the handler class in the file content
        with open('api/bot.py', 'r', encoding='utf-8') as f:
            content = f.read()

        if 'class handler(BaseHTTPRequestHandler):' in content:
            print("✅ Handler class definition is correct in api/bot.py")
            return True
        else:
            print("❌ Handler class definition is missing or incorrect in api/bot.py")
            return False
            
    except FileNotFoundError:
        print("❌ api/bot.py not found")
        return False
    except Exception as e:
        print(f"❌ Handler structure test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Vercel deployment configuration...")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Vercel Config & Imports", test_imports),
        ("Handler Structure", test_handler_structure)
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        result = test_func()
        if not result:
            all_passed = False
            
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! The structure seems correct for Vercel deployment.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        sys.exit(1)
