#!/usr/bin/env python3
"""
Test script to verify sticker pack fixes
"""

import asyncio
import logging
import sys
import os

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from index import render_image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_webp_generation():
    """Test that render_image produces WebP format"""
    logger.info("Testing WebP generation...")
    
    try:
        # Test with sample text
        webp_bytes = await render_image(
            text="تست استیکر",
            v_pos="center", 
            h_pos="center",
            font_key="Default",
            color_hex="#FFFFFF",
            size_key="medium",
            for_telegram_pack=True
        )
        
        # Verify WebP format
        if webp_bytes.startswith(b'RIFF') and b'WEBP' in webp_bytes[8:12]:
            logger.info(f"✅ WebP format verified - Size: {len(webp_bytes)} bytes")
            return True
        else:
            logger.error("❌ Generated image is not in WebP format")
            return False
            
    except Exception as e:
        logger.error(f"❌ WebP generation test failed: {e}")
        return False

async def test_multiple_renders():
    """Test multiple sticker renders to simulate pack creation"""
    logger.info("Testing multiple sticker renders...")
    
    test_texts = ["استیکر اول", "استیکر دوم", "استیکر سوم"]
    success_count = 0
    
    for i, text in enumerate(test_texts):
        try:
            webp_bytes = await render_image(
                text=text,
                v_pos="center",
                h_pos="center", 
                font_key="Default",
                color_hex="#FFFFFF",
                size_key="medium",
                for_telegram_pack=True
            )
            
            if webp_bytes.startswith(b'RIFF') and b'WEBP' in webp_bytes[8:12]:
                success_count += 1
                logger.info(f"✅ Sticker {i+1} generated successfully - {len(webp_bytes)} bytes")
            else:
                logger.error(f"❌ Sticker {i+1} not in WebP format")
                
        except Exception as e:
            logger.error(f"❌ Sticker {i+1} generation failed: {e}")
    
    success_rate = (success_count / len(test_texts)) * 100
    logger.info(f"📊 Multiple render test: {success_count}/{len(test_texts)} successful ({success_rate}%)")
    
    return success_rate == 100

async def main():
    """Run all tests"""
    logger.info("🧪 Starting sticker pack fix verification tests...")
    
    tests = [
        ("WebP Generation", test_webp_generation),
        ("Multiple Renders", test_multiple_renders),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("📋 TEST SUMMARY")
    logger.info("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    success_rate = (passed / total) * 100
    logger.info(f"\n🎯 Overall: {passed}/{total} tests passed ({success_rate}%)")
    
    if success_rate == 100:
        logger.info("🎉 All tests passed! Sticker pack fixes are working correctly.")
    else:
        logger.warning("⚠️ Some tests failed. Review the issues above.")
    
    return success_rate == 100

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)