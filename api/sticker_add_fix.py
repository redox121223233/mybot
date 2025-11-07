#!/usr/bin/env python3
"""
Enhanced sticker addition to pack with multiple attempts and better error handling
"""

import asyncio
import logging
from telegram.error import BadRequest, TelegramError

logger = logging.getLogger(__name__)

async def add_sticker_to_pack_enhanced(context, user_id: int, pack_short_name: str, file_id: str, 
                                      emoji: str = "😊", max_attempts: int = 3) -> bool:
    """
    Enhanced function to add sticker to pack with multiple attempts and detailed logging
    """
    
    logger.info(f"Starting enhanced sticker addition for user {user_id}, pack: {pack_short_name}")
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_attempts} to add sticker to pack...")
            
            # Add delay between attempts to avoid rate limiting
            if attempt > 0:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s
            
            # Try to add sticker to set
            await context.bot.add_sticker_to_set(
                user_id=user_id,
                name=pack_short_name,
                sticker=file_id,
                emojis=emoji
            )
            
            logger.info(f"✅ SUCCESS: Sticker added to pack {pack_short_name} on attempt {attempt + 1}")
            return True
            
        except BadRequest as e:
            error_message = str(e)
            logger.warning(f"BadRequest on attempt {attempt + 1}: {error_message}")
            
            # Check for specific errors that we can handle
            if "STICKERSET_INVALID" in error_message:
                logger.error("Pack does not exist or is inaccessible")
                return False
            elif "STICKERS_TOO_MUCH" in error_message:
                logger.error("Sticker pack is full (120 stickers limit)")
                return False
            elif "STICKER_EMOJI_INVALID" in error_message:
                logger.warning("Invalid emoji, trying with default emoji")
                # Retry with default emoji on next attempt
                emoji = "😊"
                continue
            elif "PEER_ID_INVALID" in error_message:
                logger.error("User ID is invalid")
                return False
                
        except TelegramError as e:
            error_message = str(e)
            logger.warning(f"TelegramError on attempt {attempt + 1}: {error_message}")
            
            # Check for rate limiting
            if "Too many requests" in error_message or "FLOOD_WAIT" in error_message:
                if attempt < max_attempts - 1:
                    wait_time = 5 + (attempt * 3)  # 5s, 8s, 11s
                    logger.info(f"Rate limited, waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                    
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}", exc_info=True)
            if attempt < max_attempts - 1:
                continue
    
    logger.error(f"❌ FAILED: Could not add sticker to pack after {max_attempts} attempts")
    return False

async def verify_pack_exists(context, pack_short_name: str) -> bool:
    """
    Verify that the sticker pack exists and is accessible
    """
    try:
        await context.bot.get_sticker_set(name=pack_short_name)
        logger.info(f"Pack {pack_short_name} exists and is accessible")
        return True
    except Exception as e:
        logger.warning(f"Pack {pack_short_name} verification failed: {e}")
        return False

async def get_pack_sticker_count(context, pack_short_name: str) -> int:
    """
    Get the current number of stickers in a pack
    """
    try:
        sticker_set = await context.bot.get_sticker_set(name=pack_short_name)
        count = len(sticker_set.stickers)
        logger.info(f"Pack {pack_short_name} has {count} stickers")
        return count
    except Exception as e:
        logger.warning(f"Could not get sticker count for {pack_short_name}: {e}")
        return 0

def is_pack_full(count: int, limit: int = 120) -> bool:
    """
    Check if pack is at or near capacity
    """
    return count >= limit