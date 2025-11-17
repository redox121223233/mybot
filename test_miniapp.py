#!/usr/bin/env python3
"""
Test script to check mini app functionality
"""
import re

def test_miniapp_fixes():
    """Test the fixes applied to mini app"""
    
    print("🧪 Testing Mini App Fixes...")
    
    # Read JavaScript file
    with open('public/js/sticker-creator.js', 'r') as f:
        js_content = f.read()
    
    # Read HTML file
    with open('templates/miniapp.html', 'r') as f:
        html_content = f.read()
    
    # Test 1: packName vs packageName fix
    if 'document.getElementById(\'packageName\')' in js_content:
        print("✅ packName -> packageName fix applied")
    else:
        print("❌ packName -> packageName fix missing")
        return False
    
    # Test 2: selectedColor usage
    if 'this.selectedColor' in js_content:
        print("✅ selectedColor variable added")
    else:
        print("❌ selectedColor variable missing")
        return False
    
    # Test 3: Color picker event listener
    if 'color-option' in js_content and 'dataset.color' in js_content:
        print("✅ Color picker event listener added")
    else:
        print("❌ Color picker event listener missing")
        return False
    
    # Test 4: Remove textColor references
    if 'textColor' not in js_content:
        print("✅ textColor references removed")
    else:
        print("❌ textColor references still present")
        return False
    
    # Test 5: Check HTML elements exist
    required_elements = ['packageName', 'stickerText', 'fontSize']
    for element in required_elements:
        if f'id="{element}"' in html_content:
            print(f"✅ {element} input exists in HTML")
        else:
            print(f"❌ {element} input missing in HTML")
            return False
    
    # Test 6: Check color options exist
    if 'color-option' in html_content and 'data-color' in html_content:
        print("✅ Color picker exists in HTML")
    else:
        print("❌ Color picker missing in HTML")
        return False
    
    print("\n🎉 All mini app tests passed!")
    return True

if __name__ == "__main__":
    test_miniapp_fixes()