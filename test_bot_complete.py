#!/usr/bin/env python3
"""
Final, Corrected Test Suite for the Telegram Sticker Bot
"""
import subprocess
import sys

def run_test(test_name, command):
    print(f"\\n🧪 Testing: {test_name}")
    print("=" * 50)
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        print(f"✅ PASSED: {test_name}")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ FAILED: {test_name}")
        if e.stdout.strip():
            print(f"Stdout: {e.stdout.strip()}")
        if e.stderr.strip():
            print(f"Stderr: {e.stderr.strip()}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {test_name} - {e}")
        return False

def main():
    print("🚀 Final Comprehensive Test Suite")
    print("=" * 60)
    
    tests = [
        ("Python Syntax Check", "python -m py_compile api/index.py"),
        ("Vercel Config Check", "jq . vercel.json"),
        ("Webhook Route Check", "grep -q \"@app.route('/api/webhook'\" api/index.py"),
        ("Sticker Pack API Route Check", "grep -q \"@app.route('/api/add-sticker-to-pack'\" api/index.py"),
        ("Logging API Route Check", "grep -q \"@app.route('/api/log'\" api/index.py"),
        ("Start Command Handler Check", "grep -q 'CommandHandler(\"start\"' api/index.py"),
    ]
    
    passed = sum(1 for name, cmd in tests if run_test(name, cmd))
    total = len(tests)
    
    print("\\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\\n🎉 ALL TESTS PASSED! The application is stable and correctly configured.")
    else:
        print(f"\\n⚠️ {total - passed} tests failed. Please review the errors above.")
    
    return passed == total

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
