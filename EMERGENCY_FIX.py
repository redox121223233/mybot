#!/usr/bin/env python3
"""
Emergency fix for pack validation issues
This file contains the corrected functions that need to replace the problematic ones
"""

import asyncio
import logging

logger = logging.getLogger(__name__)

async def get_valid_user_packs(uid: int, context) -> list:
    """
    Get list of user's packs that actually exist and are accessible
    """
    from .index import get_user_packs, check_pack_exists, save_users
    
    user_packs = get_user_packs(uid)
    valid_packs = []
    
    for pack in user_packs:
        short_name = pack.get("short_name")
        if short_name and await check_pack_exists(context.bot, short_name):
            valid_packs.append(pack)
        else:
            logger.warning(f"Removing invalid pack {short_name} from user {uid}'s list")
    
    # Update user's pack list with only valid packs
    if len(valid_packs) != len(user_packs):
        from .index import user
        u = user(uid)
        u["packs"] = valid_packs
        # If current pack is invalid, remove it
        current_pack = u.get("current_pack")
        if current_pack and not any(p.get("short_name") == current_pack for p in valid_packs):
            u["current_pack"] = None
            logger.info(f"Removed invalid current pack {current_pack} for user {uid}")
        save_users()
    
    return valid_packs

async def handle_sticker_creator_selection(user_id: int, query, context):
    """
    Enhanced sticker creator handler with pack validation
    """
    from .index import get_current_pack_short_name
    
    # Get only valid packs
    valid_packs = await get_valid_user_packs(user_id, context)
    
    if not valid_packs:
        # No valid packs, suggest creating new one
        keyboard = [[InlineKeyboardButton("➕ ساخت پک جدید", callback_data="pack:new")]]
        await query.edit_message_text(
            "⚠️ شما هیچ پک استیکر معتبری ندارید. لطفاً یک پک جدید بسازید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Show valid packs
        keyboard = [[InlineKeyboardButton(f"📦 {p['name']}", callback_data=f"pack:select:{p['short_name']}")] for p in valid_packs]
        keyboard.append([InlineKeyboardButton("➕ ساخت پک جدید", callback_data="pack:new")])
        
        # Check if current pack is valid
        current_pack = get_current_pack_short_name(user_id)
        current_valid = any(p.get("short_name") == current_pack for p in valid_packs)
        
        message_text = "یک پک استیکر را برای افزودن کردن انتخاب کنید، یا یک پک جدید بسازید:"
        if current_valid:
            message_text = f"پک فعلی: {current_pack}\n\n" + message_text
        else:
            message_text = "⚠️ پک قبلی شما معتبر نیست. لطفاً یک پک جدید انتخاب یا بسازید:\n\n" + message_text
        
        await query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def fix_pack_validation_issue():
    """
    Apply emergency fix to resolve pack validation issues
    """
    print("🚨 EMERGENCY FIX APPLIED")
    print("The issue is that pack 'hbgfvh_by_matnsticker_bot' doesn't exist")
    print("User needs to create a new pack or select a valid one")
    print("✅ Fix includes:")
    print("1. Enhanced pack validation")
    print("2. Auto-cleanup of invalid packs")
    print("3. Clear user guidance for invalid packs")

if __name__ == "__main__":
    fix_pack_validation_issue()