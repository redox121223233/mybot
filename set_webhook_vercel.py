#!/usr/bin/env python3
"""
Set webhook for Telegram bot on Vercel deployment
"""

import asyncio
import os
import sys
from telegram import Bot
import requests

async def set_webhook():
    """Set webhook for the bot after Vercel deployment."""
    
    # Get environment variables
    bot_token = os.environ.get('BOT_TOKEN')
    vercel_url = os.environ.get('VERCEL_URL')
    
    if not bot_token:
        print("❌ BOT_TOKEN environment variable is required")
        return False
        
    if not vercel_url:
        print("❌ VERCEL_URL environment variable is required")
        print("   This should be your Vercel deployment URL")
        return False
    
    # Construct webhook URL
    webhook_url = f"https://{vercel_url}/api"
    
    print(f"🔗 Setting webhook to: {webhook_url}")
    
    try:
        bot = Bot(token=bot_token)
        
        # Set webhook
        info = await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query", "inline_query", "chosen_inline_result"],
            drop_pending_updates=True
        )
        
        if info:
            print("✅ Webhook set successfully!")
            print(f"📍 Webhook URL: {webhook_url}")
            print(f"🤖 Bot info: {await bot.get_me()}")
            return True
        else:
            print("❌ Failed to set webhook")
            return False
            
    except Exception as e:
        print(f"❌ Error setting webhook: {e}")
        return False

async def get_webhook_info():
    """Get current webhook information."""
    bot_token = os.environ.get('BOT_TOKEN')
    
    if not bot_token:
        print("❌ BOT_TOKEN environment variable is required")
        return
        
    try:
        bot = Bot(token=bot_token)
        info = await bot.get_webhook_info()
        
        print("📋 Current Webhook Info:")
        print(f"   URL: {info.url}")
        print(f"   Custom Certificate: {info.has_custom_certificate}")
        print(f"   Pending Updates: {info.pending_update_count}")
        print(f"   Error Date: {info.error_date}")
        print(f"   Error Message: {info.error_message}")
        print(f"   Max Connections: {info.max_connections}")
        print(f"   Allowed Updates: {info.allowed_updates}")
        
    except Exception as e:
        print(f"❌ Error getting webhook info: {e}")

async def delete_webhook():
    """Delete webhook to switch back to polling."""
    bot_token = os.environ.get('BOT_TOKEN')
    
    if not bot_token:
        print("❌ BOT_TOKEN environment variable is required")
        return False
        
    try:
        bot = Bot(token=bot_token)
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Webhook deleted successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False

async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python set_webhook_vercel.py set     - Set webhook")
        print("  python set_webhook_vercel.py info    - Get webhook info")
        print("  python set_webhook_vercel.py delete  - Delete webhook")
        return
    
    command = sys.argv[1].lower()
    
    if command == "set":
        await set_webhook()
    elif command == "info":
        await get_webhook_info()
    elif command == "delete":
        await delete_webhook()
    else:
        print("❌ Unknown command. Use 'set', 'info', or 'delete'")

if __name__ == "__main__":
    asyncio.run(main())