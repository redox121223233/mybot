#!/usr/bin/env python3
"""
Simple pack checker that bypasses telegram library issues
"""

import asyncio
import aiohttp
import logging

logger = logging.getLogger(__name__)

async def check_pack_exists_direct(bot_token: str, short_name: str) -> bool:
    """
    Check pack existence by calling Telegram API directly
    Bypasses python-telegram-bot library issues
    """
    
    url = f"https://api.telegram.org/bot{bot_token}/getStickerSet"
    params = {"name": short_name}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get("ok"):
                    result = data.get("result", {})
                    stickers = result.get("stickers", [])
                    logger.info(f"✅ Pack {short_name} exists with {len(stickers)} stickers (direct API)")
                    return True
                else:
                    error_code = data.get("error_code")
                    error_desc = data.get("description", "")
                    
                    if "stickerset_invalid" in error_desc.lower():
                        logger.error(f"🚨 Pack {short_name} does not exist (direct API)")
                        return False
                    else:
                        logger.warning(f"⚠️ API error for {short_name}: {error_desc}")
                        return False
                        
    except Exception as e:
        logger.error(f"❌ Direct API check failed for {short_name}: {e}")
        return False

async def get_pack_info_direct(bot_token: str, short_name: str) -> dict:
    """
    Get detailed pack info using direct API call
    """
    
    url = f"https://api.telegram.org/bot{bot_token}/getStickerSet"
    params = {"name": short_name}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data.get("ok"):
                    result = data.get("result", {})
                    return {
                        "exists": True,
                        "name": result.get("name"),
                        "title": result.get("title"),
                        "sticker_count": len(result.get("stickers", [])),
                        "is_animated": result.get("is_animated", False),
                        "is_video": result.get("is_video", False)
                    }
                else:
                    return {
                        "exists": False,
                        "error": data.get("description", "Unknown error")
                    }
                    
    except Exception as e:
        logger.error(f"❌ Failed to get pack info for {short_name}: {e}")
        return {
            "exists": False,
            "error": str(e)
        }

# Quick test function
def test_direct_api():
    """
    Test the direct API approach
    """
    print("🔧 Direct Telegram API Checker")
    print("This bypasses python-telegram-bot library issues")
    print("Uses aiohttp for direct HTTP calls to Telegram API")