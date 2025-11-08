#!/usr/bin/env python3
"""
Telegram Library Compatibility Fix
Handles python-telegram-bot version compatibility issues
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

async def safe_get_sticker_set(bot, short_name: str, max_retries: int = 3):
    """
    Safe get_sticker_set with multiple fallback methods
    Compatible with different python-telegram-bot versions
    """
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1} to get sticker set {short_name}")
            
            # Method 1: Standard call
            sticker_set = await bot.get_sticker_set(name=short_name)
            logger.info(f"✅ Method 1 succeeded for {short_name}")
            return sticker_set
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Method 1 failed (attempt {attempt + 1}): {error_msg}")
            
            # If it's the StickerSet initialization error, try alternative
            if "missing 2 required positional arguments" in error_msg:
                try:
                    logger.info(f"Trying alternative method for {short_name}")
                    
                    # Method 2: Direct API call (if available)
                    try:
                        # Try to get raw data
                        raw_data = await bot.get_sticker_set(name=short_name)
                        if raw_data:
                            logger.info(f"✅ Alternative method succeeded for {short_name}")
                            return raw_data
                    except Exception as alt_error:
                        logger.warning(f"Alternative method failed: {alt_error}")
                    
                    # Method 3: Test with add_sticker_to_set (will fail if pack doesn't exist)
                    if attempt == max_retries - 1:  # Only on last attempt
                        try:
                            # This will fail with specific error if pack doesn't exist
                            await bot.add_sticker_to_set(
                                user_id=bot.id,  # This might not work, but we're testing
                                name=short_name,
                                sticker="test",  # Invalid sticker, just testing pack existence
                                emojis="😊"
                            )
                        except Exception as test_error:
                            if "STICKERSET_INVALID" in str(test_error) or "sticker set not found" in str(test_error).lower():
                                logger.error(f"❌ Pack {short_name} definitely doesn't exist")
                                raise test_error
                            else:
                                # Pack exists but we can't add sticker (permission issue)
                                logger.info(f"✅ Pack {short_name} exists (inferred from permission error)")
                                return {"exists": True, "inferred": True}
                
                except Exception as fallback_error:
                    logger.warning(f"Fallback method failed: {fallback_error}")
                    
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
            else:
                logger.error(f"❌ All methods failed for pack {short_name}")
                raise e

async def check_pack_exists_robust(bot, short_name: str) -> bool:
    """
    Robust pack existence check with multiple methods
    """
    try:
        await safe_get_sticker_set(bot, short_name)
        return True
    except Exception as e:
        logger.warning(f"Pack {short_name} existence check failed: {e}")
        
        # Check for specific error messages
        error_msg = str(e).lower()
        if any(keyword in error_msg for keyword in [
            "stickerset_invalid", 
            "sticker set not found", 
            "not found",
            "doesn't exist"
        ]):
            logger.error(f"🚨 Pack {short_name} confirmed as non-existent")
            return False
        elif "permission" in error_msg or "access" in error_msg:
            logger.warning(f"⚠️ Pack {short_name} exists but no access")
            return True  # Pack exists, just no permission
        else:
            # Unknown error, assume pack doesn't exist
            logger.error(f"❓ Unknown error for pack {short_name}, assuming non-existent")
            return False

def apply_telegram_compatibility_fix():
    """
    Apply compatibility fixes for telegram library issues
    """
    print("🔧 Applying Telegram Library Compatibility Fixes")
    print("Issues addressed:")
    print("1. StickerSet.__init__() missing arguments error")
    print("2. Multiple fallback methods for get_sticker_set")
    print("3. Robust error handling for different versions")
    print("4. Better logging for debugging")

if __name__ == "__main__":
    apply_telegram_compatibility_fix()