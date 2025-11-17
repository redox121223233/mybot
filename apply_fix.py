#!/usr/bin/env python3
"""
Quick script to apply the InputSticker fix to any bot installation
"""
import os
import sys
import re

def fix_bot_file(file_path):
    """Apply the InputSticker fix to the bot file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if InputSticker is already imported
        if 'from telegram import.*InputSticker' not in content:
            # Add InputSticker to imports
            content = re.sub(
                r'from telegram import (.*)',
                r'from telegram import \1, InputSticker',
                content
            )
            print("✅ Added InputSticker import")
        
        # Fix add_sticker_to_set calls
        old_pattern = r'await bot\.add_sticker_to_set\([^)]*sticker=sticker_bytes[^)]*\)'
        new_replacement = '''# Create InputSticker object for the new API format
                input_sticker = InputSticker(
                    sticker=sticker_bytes,
                    emoji_list=['😊']
                )
                
                await bot.add_sticker_to_set(user_id=user_id, name=full_pack_name, sticker=input_sticker)'''
        
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_replacement, content)
            print("✅ Fixed add_sticker_to_set call")
        
        # Fix create_new_sticker_set calls
        old_create_pattern = r'await bot\.create_new_sticker_set\([^)]*sticker=sticker_bytes[^)]*emojis=\[\'😊\'\][^)]*\)'
        new_create_replacement = '''# Create InputSticker object for the new API format
                input_sticker = InputSticker(
                    sticker=sticker_bytes,
                    emoji_list=['😊']
                )
                
                await bot.create_new_sticker_set(
                    user_id=user_id, 
                    name=full_pack_name, 
                    title=pack_name, 
                    sticker=input_sticker
                )'''
        
        if re.search(old_create_pattern, content):
            content = re.sub(old_create_pattern, new_create_replacement, content)
            print("✅ Fixed create_new_sticker_set call")
        
        # Write the fixed content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing file: {e}")
        return False

def main():
    print("🔧 Applying InputSticker fix to your Telegram bot...")
    
    # Look for the main bot file
    possible_paths = [
        'index.py',
        'main.py', 
        'app.py',
        'api/index.py',
        'bot.py'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"📁 Found bot file: {path}")
            if fix_bot_file(path):
                print("✅ Fix applied successfully!")
                print("🔄 Please restart your bot to apply the changes.")
                return
            else:
                print("❌ Failed to apply fix.")
                return
    
    # If no standard files found, ask user for path
    print("❓ Could not find the main bot file.")
    print("Please provide the path to your bot's main Python file:")
    user_path = input("> ").strip()
    
    if os.path.exists(user_path):
        if fix_bot_file(user_path):
            print("✅ Fix applied successfully!")
            print("🔄 Please restart your bot to apply the changes.")
        else:
            print("❌ Failed to apply fix.")
    else:
        print("❌ File not found.")

if __name__ == "__main__":
    main()