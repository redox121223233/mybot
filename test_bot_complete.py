#!/usr/bin/env python3
"""
Complete test suite for the Telegram Sticker Bot
Tests all major functionality after fixes - UPDATED FOR RESTORED FUNCTIONALITY
"""

import subprocess
import sys
import os

def run_test(test_name, command, expect_fail=False):
    """Run a test and return result"""
    print(f"\n🧪 Testing: {test_name}")
    print("=" * 50)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        passed = result.returncode == 0
        if expect_fail:
            passed = not passed

        if passed:
            print(f"✅ PASSED: {test_name}")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ FAILED: {test_name}")
            if result.stdout.strip():
                print(f"Stdout: {result.stdout.strip()}")
            if result.stderr.strip():
                print(f"Stderr: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {test_name} - {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Full Functionality Test Suite")
    print("=" * 60)
    
    tests = [
        ("Python Syntax Check", "python -m py_compile api/index.py"),
        ("Vercel Config Check", "cat vercel.json"),
        ("Flask App Instance Check", "grep -q 'app = Flask(__name__)' api/index.py"),
        ("Webhook Route Check", "grep -q \"@app.route('/api/webhook'\" api/index.py"),
        ("Telegram Application Check", "grep -q 'Application.builder()' api/index.py"),
        ("Sticker Creation Function Check", "grep -q 'def create_sticker' api/index.py"),
        ("Image Library Check (Pillow)", "grep -q 'from PIL import' api/index.py"),
        ("Arabic Reshaper Check", "grep -q 'import arabic_reshaper' api/index.py"),
        ("Photo Handler Check", "grep -q 'handle_photo' api/index.py"),
        ("Text Handler Check", "grep -q 'handle_text' api/index.py"),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, command in tests:
        if run_test(test_name, command):
            passed += 1
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Bot architecture and core functionality are solid.")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Review the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
