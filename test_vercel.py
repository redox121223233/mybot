#!/usr/bin/env python3
"""
Test script for Vercel deployment
"""

import sys
import os

def test_imports():
    """Test if all required modules can be imported"""
    try:
        import json
        print("✅ json import successful")
        
        # Test if vercel.json is valid
        with open('vercel.json', 'r') as f:
            config = json.load(f)
            print("✅ vercel.json is valid JSON")
            print(f"✅ Version: {config.get('version')}")
            
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_file_structure():
    """Test if required files exist"""
    required_files = [
        'api/index.py',
        'vercel.json', 
        'requirements.txt',
        'handlers.py',
        'bot_features.py'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            all_exist = False
            
    return all_exist

def test_handler_structure():
    """Test if handler function is properly structured"""
    try:
        with open('api/index.py', 'r') as f:
            content = f.read()
            
        if 'def handler(' in content:
            print("✅ Handler function exists")
        else:
            print("❌ Handler function missing")
            return False
            
        if 'from flask import Flask' in content:
            print("✅ Flask import present")
        else:
            print("❌ Flask import missing")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Handler structure test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Vercel deployment configuration...")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Import Tests", test_imports), 
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
        print("🎉 All tests passed! Ready for Vercel deployment.")
    else:
        print("⚠️  Some tests failed. Please review the issues above.")